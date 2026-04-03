"""
generate_eval_set.py — Build a synthetic QA evaluation set for RAGAS.

For each sampled article, prompts the LLM (via Groq) to generate a realistic
user question that can be answered from the article's content, plus the
ground-truth answer.  This produces data/eval/qa_pairs.jsonl.

Run once after the initial corpus is built; re-run to extend the eval set
when significantly more articles have been ingested.

RAGAS requires:
  question        — the user query
  answer          — LLM answer (filled in by run_ragas_eval.py)
  contexts        — retrieved chunks (filled in by run_ragas_eval.py)
  ground_truth    — the reference answer generated here
"""

import json
import logging
import os
import random
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT       = Path(__file__).parent.parent
RAW_DIR    = ROOT / "data" / "raw"
EVAL_DIR   = ROOT / "data" / "eval"
ARTICLES_F = RAW_DIR / "articles.jsonl"
QA_FILE    = EVAL_DIR / "qa_pairs.jsonl"

EVAL_DIR.mkdir(parents=True, exist_ok=True)

# How many QA pairs to generate (more = better eval, more API calls)
N_PAIRS = 50
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a supply chain analyst generating evaluation data.
Given an article excerpt, produce a realistic question a logistics professional
might ask, and the correct answer grounded in the article text.

Respond with valid JSON only:
{
  "question": "...",
  "ground_truth": "..."
}

Rules:
- The question must be answerable from the article alone
- The ground_truth must be factual and specific (names, figures, dates where present)
- Do not make up information not in the article
- Questions should be about disruptions, costs, routes, volumes, or operational impacts"""


def load_articles() -> list[dict]:
    articles = []
    if not ARTICLES_F.exists():
        return articles
    with open(ARTICLES_F) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    articles.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return articles


def load_existing_question_ids() -> set[str]:
    if not QA_FILE.exists():
        return set()
    ids = set()
    with open(QA_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    ids.add(json.loads(line)["article_id"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return ids


def generate_qa_pair(client: Groq, article: dict) -> dict | None:
    # Truncate content to first 1500 chars (sufficient for question generation)
    excerpt = article["content"][:1500]
    user_msg = f"Title: {article['title']}\n\nContent:\n{excerpt}"

    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.4,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        parsed = json.loads(raw)

        return {
            "article_id":   article["id"],
            "source":       article["source"],
            "article_url":  article["url"],
            "published":    article["published"],
            "question":     parsed["question"],
            "ground_truth": parsed["ground_truth"],
            # Filled in by run_ragas_eval.py:
            "answer":    None,
            "contexts":  None,
        }
    except Exception as exc:
        logger.warning(f"QA generation failed for {article['id']}: {exc}")
        return None


def main():
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        logger.error("GROQ_API_KEY not set in .env — cannot generate eval set.")
        return

    client = Groq(api_key=api_key)

    articles    = load_articles()
    existing    = load_existing_question_ids()
    candidates  = [a for a in articles if a["id"] not in existing
                   and len(a["content"]) >= 300]

    if not candidates:
        logger.info("No new articles to generate QA pairs for.")
        return

    sample = random.sample(candidates, min(N_PAIRS, len(candidates)))
    logger.info(f"Generating {len(sample)} QA pairs...")

    generated = 0
    with open(QA_FILE, "a") as f:
        for i, article in enumerate(sample):
            pair = generate_qa_pair(client, article)
            if pair:
                f.write(json.dumps(pair) + "\n")
                generated += 1
            if (i + 1) % 10 == 0:
                logger.info(f"  {i+1}/{len(sample)} processed ({generated} generated)")

    logger.info(f"Done. Added {generated} QA pairs → {QA_FILE}")
    logger.info("Run run_ragas_eval.py to score the RAG pipeline against this set.")


if __name__ == "__main__":
    main()
