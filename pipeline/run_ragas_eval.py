"""
run_ragas_eval.py — Score the RAG pipeline with RAGAS metrics.

For each QA pair in data/eval/qa_pairs.jsonl:
  1. Run the RAG retrieval pipeline to get contexts
  2. Run the RAG generation step to get the answer
  3. Score with RAGAS (faithfulness, answer_relevancy, context_precision,
     context_recall)

Writes results to data/eval/ragas_results.json — this file is served by
the API and displayed in the frontend Model Scorecard.

RAGAS metrics explained:
  faithfulness       — does the answer contain only claims supported by contexts?
  answer_relevancy   — does the answer address the question?
  context_precision  — are the retrieved contexts actually relevant?
  context_recall     — do the contexts cover the ground truth information?

Reference: Es et al. "RAGAS: Automated Evaluation of Retrieval Augmented
Generation", arXiv:2309.15217, 2023.
"""

import json
import logging
import os
from pathlib import Path

from datasets import Dataset
from dotenv import load_dotenv
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT      = Path(__file__).parent.parent
EVAL_DIR  = ROOT / "data" / "eval"
QA_FILE   = EVAL_DIR / "qa_pairs.jsonl"
RESULTS_F      = EVAL_DIR / "ragas_results.json"
CACHE_F        = EVAL_DIR / "rag_cache.jsonl"
SCORE_CACHE_F  = EVAL_DIR / "ragas_score_cache.json"

# Import the retrieval + generation functions from the API
import sys
sys.path.insert(0, str(ROOT / "api"))
from rag import retrieve, generate_answer   # noqa: E402


def load_cache() -> dict[str, dict]:
    """Load previously computed RAG outputs keyed by question."""
    cache = {}
    if not CACHE_F.exists():
        return cache
    with open(CACHE_F) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    cache[entry["question"]] = entry
                except json.JSONDecodeError:
                    pass
    return cache


def load_qa_pairs() -> list[dict]:
    pairs = []
    if not QA_FILE.exists():
        return pairs
    with open(QA_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    pairs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return pairs


def main():
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        logger.error("GROQ_API_KEY not set — cannot run evaluation.")
        return

    pairs = load_qa_pairs()
    if not pairs:
        logger.error(f"No QA pairs found at {QA_FILE}. Run generate_eval_set.py first.")
        return

    cache = load_cache()
    n_cached = sum(1 for p in pairs if p["question"] in cache)
    logger.info(f"RAG cache: {n_cached}/{len(pairs)} pairs already computed, {len(pairs) - n_cached} remaining.")

    questions, answers, contexts_list, ground_truths = [], [], [], []

    with open(CACHE_F, "a") as cache_file:
        for i, pair in enumerate(pairs):
            question = pair["question"]

            if question in cache:
                entry = cache[question]
                answer   = entry["answer"]
                contexts = entry["contexts"]
            else:
                retrieved = retrieve(question, n_results=5)
                answer    = generate_answer(question, retrieved)
                contexts  = [r["text"] for r in retrieved]
                cache_file.write(json.dumps({"question": question, "answer": answer, "contexts": contexts}) + "\n")
                cache_file.flush()

            questions.append(question)
            answers.append(answer)
            contexts_list.append(contexts)
            ground_truths.append(pair["ground_truth"])

            if (i + 1) % 10 == 0:
                logger.info(f"  {i+1}/{len(pairs)} processed")

    logger.info("Scoring with RAGAS...")

    dataset = Dataset.from_dict({
        "question":     questions,
        "answer":       answers,
        "contexts":     contexts_list,
        "ground_truth": ground_truths,
    })

    # RAGAS uses the LLM specified via OPENAI_API_KEY by default;
    # we override to use Groq via LangChain's ChatGroq wrapper
    from langchain_groq import ChatGroq
    from langchain_huggingface import HuggingFaceEmbeddings
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper

    llm = LangchainLLMWrapper(ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=api_key,
        temperature=0,
    ))

    embeddings = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    )

    if SCORE_CACHE_F.exists():
        logger.info("Loading raw scores from cache (previous scoring run completed)...")
        with open(SCORE_CACHE_F) as f:
            raw_scores = json.load(f)
    else:
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=llm,
            embeddings=embeddings,
        )
        raw_scores = {
            "faithfulness":      result["faithfulness"],
            "answer_relevancy":  result["answer_relevancy"],
            "context_precision": result["context_precision"],
            "context_recall":    result["context_recall"],
        }
        for k, v in raw_scores.items():
            logger.info(f"  [debug] {k}: type={type(v).__name__}, value={v}")
        with open(SCORE_CACHE_F, "w") as f:
            json.dump(raw_scores, f)
        logger.info("Raw scores cached.")

    def _mean(val) -> float:
        import math
        if isinstance(val, list):
            valid = [v for v in val if v is not None and not (isinstance(v, float) and math.isnan(v))]
            return round(sum(valid) / len(valid), 4) if valid else 0.0
        v = float(val)
        return 0.0 if math.isnan(v) else round(v, 4)

    scores = {
        "faithfulness":      _mean(raw_scores["faithfulness"]),
        "answer_relevancy":  _mean(raw_scores["answer_relevancy"]),
        "context_precision": _mean(raw_scores["context_precision"]),
        "context_recall":    _mean(raw_scores["context_recall"]),
        "n_pairs":           len(pairs),
    }

    with open(RESULTS_F, "w") as f:
        json.dump(scores, f, indent=2)

    SCORE_CACHE_F.unlink(missing_ok=True)
    logger.info("Score cache cleared.")

    logger.info("RAGAS scores:")
    for metric, score in scores.items():
        if metric != "n_pairs":
            logger.info(f"  {metric:<22s}: {score:.4f}")
    logger.info(f"Results written → {RESULTS_F}")


if __name__ == "__main__":
    main()
