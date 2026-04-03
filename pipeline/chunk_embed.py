"""
chunk_embed.py — Chunk articles and build / update the Chroma vector store.

Reads data/raw/articles.jsonl, splits each article into overlapping chunks,
embeds them with BAAI/bge-small-en-v1.5, and upserts into the Chroma
collection (skipping chunks already present by ID).

Chroma is file-backed (data/processed/chroma_db/) — the directory is
committed to the repo so the vector store ships with the code and the
API doesn't need to rebuild it at startup.

Model choice — BAAI/bge-small-en-v1.5:
  33 MB on disk, CPU-friendly, scores within ~2pts of ada-002 on MTEB.
  The large variant (bge-large, 1.3 GB) improves retrieval quality but
  won't fit on Render free tier RAM.  Switch to bge-large for local dev
  or a paid deployment by changing EMBED_MODEL below.
"""

import json
import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
RAW_DIR    = ROOT / "data" / "raw"
CHROMA_DIR = ROOT / "data" / "processed" / "chroma_db"
ARTICLES_F = RAW_DIR / "articles.jsonl"

CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# ── Config ─────────────────────────────────────────────────────────────────
EMBED_MODEL    = "BAAI/bge-small-en-v1.5"
COLLECTION     = "freightsignal"
CHUNK_SIZE     = 400      # tokens (approximate — we use character proxy)
CHUNK_OVERLAP  = 80
CHARS_PER_TOK  = 4        # rough English average
BATCH_SIZE     = 64       # embedding batch size


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping character windows (token-approximate).
    Simple sliding window — no sentence boundary detection needed for
    news articles where paragraphs are already short.
    """
    size_chars    = chunk_size * CHARS_PER_TOK
    overlap_chars = overlap * CHARS_PER_TOK

    if len(text) <= size_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size_chars, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += size_chars - overlap_chars

    return chunks


def load_articles() -> list[dict]:
    if not ARTICLES_F.exists():
        logger.error(f"Article store not found: {ARTICLES_F}")
        logger.error("Run fetch_articles.py first.")
        return []
    articles = []
    with open(ARTICLES_F) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    articles.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return articles


def build_chunks(articles: list[dict]) -> tuple[list[str], list[str], list[dict]]:
    """
    Returns (ids, texts, metadatas) ready for Chroma upsert.
    Chunk ID format: {article_id}_{chunk_index}
    """
    ids, texts, metadatas = [], [], []
    for article in articles:
        body     = f"{article['title']}\n\n{article['content']}"
        chunks   = chunk_text(body)
        for i, chunk in enumerate(chunks):
            chunk_id = f"{article['id']}_{i}"
            ids.append(chunk_id)
            texts.append(chunk)
            metadatas.append({
                "article_id": article["id"],
                "chunk_index": i,
                "title":      article["title"],
                "source":     article["source"],
                "url":        article["url"],
                "published":  article["published"],
                "tags":       ",".join(article.get("tags", [])),
            })
    return ids, texts, metadatas


def main():
    logger.info(f"Loading embedding model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)

    logger.info("Opening Chroma collection...")
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    articles = load_articles()
    if not articles:
        return

    logger.info(f"Building chunks from {len(articles)} articles...")
    ids, texts, metadatas = build_chunks(articles)
    logger.info(f"Total chunks: {len(ids)}")

    # Check which chunks are already in Chroma
    existing = set(collection.get(ids=ids)["ids"])
    new_mask = [i for i, cid in enumerate(ids) if cid not in existing]

    if not new_mask:
        logger.info("All chunks already in vector store — nothing to do.")
        return

    logger.info(f"Embedding {len(new_mask)} new chunks (skipping {len(existing)} existing)...")

    new_ids       = [ids[i] for i in new_mask]
    new_texts     = [texts[i] for i in new_mask]
    new_metadatas = [metadatas[i] for i in new_mask]

    # BGE models work best with this query prefix at embed time
    # (at query time, prepend "Represent this sentence for searching relevant passages: ")
    prefixed = [f"passage: {t}" for t in new_texts]

    embeddings = []
    for batch_start in range(0, len(prefixed), BATCH_SIZE):
        batch = prefixed[batch_start : batch_start + BATCH_SIZE]
        batch_embs = model.encode(batch, normalize_embeddings=True, show_progress_bar=False)
        embeddings.extend(batch_embs.tolist())
        logger.info(f"  Embedded {min(batch_start + BATCH_SIZE, len(prefixed))}/{len(prefixed)}")

    logger.info("Upserting into Chroma...")
    # Chroma upsert in batches of 500 (API limit)
    for i in range(0, len(new_ids), 500):
        collection.upsert(
            ids=new_ids[i:i+500],
            embeddings=embeddings[i:i+500],
            documents=new_texts[i:i+500],
            metadatas=new_metadatas[i:i+500],
        )

    total = collection.count()
    logger.info(f"Done. Vector store now contains {total} chunks.")


if __name__ == "__main__":
    main()
