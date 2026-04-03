"""
rag.py — Core retrieval and generation logic.

Called by both main.py (API requests) and run_ragas_eval.py (evaluation).

Pipeline:
  query → embed (bge-small) → Chroma similarity search → top-k chunks
       → rerank (bge-reranker-base cross-encoder) → top-n chunks
       → Groq Llama 3.3 70B → answer + source metadata

Reranker note:
  A cross-encoder reranker scores each (query, chunk) pair jointly, which
  is significantly more accurate than cosine similarity alone but slower.
  We retrieve 20 candidates from Chroma then rerank to 5 — this is the
  standard retrieve-then-rerank pattern (Nogueira & Cho 2019).
"""

import logging
import os
from functools import lru_cache
from pathlib import Path

import chromadb
from chromadb.config import Settings
from groq import Groq
from groq import RateLimitError
from sentence_transformers import CrossEncoder, SentenceTransformer

logger = logging.getLogger(__name__)

ROOT       = Path(__file__).parent.parent
CHROMA_DIR = ROOT / "data" / "processed" / "chroma_db"

EMBED_MODEL    = "BAAI/bge-small-en-v1.5"
RERANK_MODEL   = "BAAI/bge-reranker-base"
COLLECTION     = "freightsignal"
GROQ_MODEL     = "llama-3.1-8b-instant"

# Retrieve this many candidates from Chroma before reranking
N_RETRIEVE = 20
# Keep this many after reranking to pass to the LLM
N_FINAL    = 5

SYSTEM_PROMPT = """You are FreightSignal, an AI assistant specialising in supply chain \
and freight intelligence. Answer the user's question using ONLY the provided source \
excerpts. Be specific — cite figures, company names, and dates from the sources when \
present. If the sources don't contain enough information to answer fully, say so clearly \
rather than speculating.

Format your answer in 2–4 concise paragraphs. Do not invent information."""


@lru_cache(maxsize=1)
def _get_embed_model() -> SentenceTransformer:
    logger.info(f"Loading embedding model: {EMBED_MODEL}")
    return SentenceTransformer(EMBED_MODEL)


@lru_cache(maxsize=1)
def _get_reranker() -> CrossEncoder:
    logger.info(f"Loading reranker: {RERANK_MODEL}")
    return CrossEncoder(RERANK_MODEL)


@lru_cache(maxsize=1)
def _get_chroma_collection():
    logger.info(f"Opening Chroma at {CHROMA_DIR}")
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_collection(COLLECTION)


@lru_cache(maxsize=1)
def _get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")
    return Groq(api_key=api_key)


def retrieve(query: str, n_results: int = N_FINAL) -> list[dict]:
    """
    Embed query → Chroma ANN search → cross-encoder rerank → top n_results.

    Returns list of dicts with keys: text, title, source, url, published, score.
    """
    embed_model = _get_embed_model()
    collection  = _get_chroma_collection()
    reranker    = _get_reranker()

    # BGE query prefix (different from passage prefix used at index time)
    query_text = f"Represent this sentence for searching relevant passages: {query}"
    query_emb  = embed_model.encode(query_text, normalize_embeddings=True).tolist()

    # Step 1: ANN retrieval — get N_RETRIEVE candidates
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=min(N_RETRIEVE, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    docs      = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]   # cosine distance (lower = more similar)

    if not docs:
        return []

    # Step 2: Cross-encoder reranking
    pairs = [(query, doc) for doc in docs]
    scores = reranker.predict(pairs).tolist()

    ranked = sorted(
        zip(scores, docs, metadatas, distances),
        key=lambda x: x[0],
        reverse=True,
    )[:n_results]

    return [
        {
            "text":      doc,
            "title":     meta.get("title", ""),
            "source":    meta.get("source", ""),
            "url":       meta.get("url", ""),
            "published": meta.get("published", ""),
            "score":     round(score, 4),
        }
        for score, doc, meta, _ in ranked
    ]


def generate_answer(question: str, retrieved: list[dict]) -> str:
    """
    Generate an answer from the retrieved chunks using Groq Llama 3.3 70B.
    """
    if not retrieved:
        return "I couldn't find relevant information in the current article corpus to answer this question."

    context_block = "\n\n---\n\n".join(
        f"[Source: {r['source']} | {r['published'][:10]}]\n{r['text']}"
        for r in retrieved
    )

    user_msg = f"Sources:\n{context_block}\n\nQuestion: {question}"

    client = _get_groq_client()
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=400,
        )
    except RateLimitError as e:
        logger.warning(f"Groq rate limit hit: {e}")
        return "The AI service is temporarily rate-limited. Please try again in a few minutes."
    return resp.choices[0].message.content.strip()
