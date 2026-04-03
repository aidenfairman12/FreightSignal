"""
main.py — FreightSignal FastAPI backend.

Endpoints:
  POST /query          — RAG query: retrieve + generate
  GET  /sources        — List indexed article sources and counts
  GET  /scorecard      — RAGAS evaluation scores
  GET  /health         — Health check + corpus stats
"""

import json
import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

from rag import generate_answer, retrieve   # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT       = Path(__file__).parent.parent
EVAL_DIR   = ROOT / "data" / "eval"
RAW_DIR    = ROOT / "data" / "raw"
ARTICLES_F = RAW_DIR / "articles.jsonl"

app = FastAPI(
    title="FreightSignal API",
    description="Supply chain disruption intelligence via RAG",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your Vercel domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=500,
                          description="Natural language question about supply chain disruptions")
    n_sources: int = Field(default=5, ge=1, le=10,
                           description="Number of source chunks to retrieve")


class SourceResult(BaseModel):
    text:      str
    title:     str
    source:    str
    url:       str
    published: str
    score:     float


class QueryResponse(BaseModel):
    answer:   str
    sources:  list[SourceResult]
    question: str


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """
    Main RAG endpoint. Retrieves relevant article chunks and generates
    a grounded answer using Llama 3.3 70B via Groq.
    """
    try:
        retrieved = retrieve(req.question, n_results=req.n_sources)
        answer    = generate_answer(req.question, retrieved)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}")

    return QueryResponse(
        question=req.question,
        answer=answer,
        sources=[SourceResult(**r) for r in retrieved],
    )


@app.get("/sources")
async def sources():
    """Article corpus summary: total count, sources breakdown, date range."""
    if not ARTICLES_F.exists():
        return {"total": 0, "by_source": {}, "date_range": None}

    total      = 0
    by_source: dict[str, int] = {}
    dates: list[str] = []

    with open(ARTICLES_F) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                article = json.loads(line)
                total += 1
                src = article.get("source", "Unknown")
                by_source[src] = by_source.get(src, 0) + 1
                if pub := article.get("published"):
                    dates.append(pub)
            except json.JSONDecodeError:
                pass

    return {
        "total":      total,
        "by_source":  by_source,
        "date_range": {
            "earliest": min(dates) if dates else None,
            "latest":   max(dates) if dates else None,
        },
    }


@app.get("/scorecard")
async def scorecard():
    """
    RAGAS evaluation scores from the last evaluation run.
    Returns null scores if evaluation hasn't been run yet.
    """
    results_file = EVAL_DIR / "ragas_results.json"
    if not results_file.exists():
        return {
            "available": False,
            "message":   "Evaluation not yet run. Execute run_ragas_eval.py to generate scores.",
            "scores":    None,
        }

    try:
        import math
        with open(results_file) as f:
            scores = json.loads(f.read().replace("NaN", "null"))
        scores = {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in scores.items()}
        return {"available": True, "scores": scores}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load scores: {exc}")


@app.get("/health")
async def health():
    """Health check — also reports corpus and vector store stats."""
    try:
        from rag import _get_chroma_collection
        collection = _get_chroma_collection()
        chunk_count = collection.count()
    except Exception:
        chunk_count = -1

    article_count = 0
    if ARTICLES_F.exists():
        with open(ARTICLES_F) as f:
            article_count = sum(1 for line in f if line.strip())

    return {
        "status":        "ok",
        "articles":      article_count,
        "chunks":        chunk_count,
    }
