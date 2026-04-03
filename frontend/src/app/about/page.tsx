"use client";

import { useEffect, useState } from "react";
import { fetchCorpusStats, fetchScorecard } from "@/lib/api";
import type { CorpusStats, ScorecardResponse } from "@/types";
import Link from "next/link";

function MetricBar({ label, value, description }: { label: string; value: number; description: string }) {
  return (
    <div>
      <div className="flex justify-between items-baseline mb-1">
        <span className="text-sm font-medium text-white">{label}</span>
        <span className="text-sm font-mono text-emerald-400">{value.toFixed(3)}</span>
      </div>
      <div className="h-2 rounded-full bg-gray-800">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all"
          style={{ width: `${Math.round(value * 100)}%` }}
        />
      </div>
      <p className="mt-1 text-xs text-gray-500">{description}</p>
    </div>
  );
}

export default function AboutPage() {
  const [stats, setStats]       = useState<CorpusStats | null>(null);
  const [scorecard, setScorecard] = useState<ScorecardResponse | null>(null);

  useEffect(() => {
    fetchCorpusStats().then(setStats).catch(() => null);
    fetchScorecard().then(setScorecard).catch(() => null);
  }, []);

  return (
    <main className="min-h-screen bg-gray-950 text-white">
      <div className="mx-auto max-w-3xl px-4 py-12 space-y-12">
        <div>
          <Link href="/" className="text-sm text-gray-500 hover:text-gray-300 transition-colors">
            ← Home
          </Link>
          <h1 className="mt-4 text-3xl font-bold text-white">How FreightSignal works</h1>
        </div>

        {/* Pipeline */}
        <section className="space-y-4">
          <h2 className="text-lg font-semibold text-white">The RAG pipeline</h2>
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-5 font-mono text-xs text-gray-400 leading-relaxed">
            <div>RSS feeds (FreightWaves, Supply Chain Dive, JOC…)</div>
            <div className="text-gray-600 ml-4">↓ fetch_articles.py · every 6h via GitHub Actions</div>
            <div className="mt-1">Chunked article text (400 tok, 80 overlap)</div>
            <div className="text-gray-600 ml-4">↓ chunk_embed.py · BAAI/bge-small-en-v1.5</div>
            <div className="mt-1">Chroma vector store (cosine similarity)</div>
            <div className="text-gray-600 ml-4">↓ ANN retrieval · top-20 candidates</div>
            <div className="mt-1">Cross-encoder reranker (BAAI/bge-reranker-base)</div>
            <div className="text-gray-600 ml-4">↓ top-5 chunks passed to LLM</div>
            <div className="mt-1 text-emerald-400">Groq Llama 3.3 70B → grounded answer</div>
          </div>
          <p className="text-sm text-gray-400 leading-relaxed">
            The retrieve-then-rerank pattern (Nogueira &amp; Cho, 2019) uses fast approximate
            nearest-neighbour search to narrow the candidate set, then a more expensive
            cross-encoder to get accurate relevance scores. This gives significantly
            better retrieval quality than cosine similarity alone at a modest latency cost.
          </p>
        </section>

        {/* Corpus stats */}
        <section className="space-y-4">
          <h2 className="text-lg font-semibold text-white">Corpus</h2>
          {stats ? (
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-5 space-y-4">
              <div className="flex gap-8">
                <div>
                  <div className="text-3xl font-bold text-white">{stats.total.toLocaleString()}</div>
                  <div className="text-xs text-gray-500 mt-0.5">indexed articles</div>
                </div>
                {stats.date_range?.latest && (
                  <div>
                    <div className="text-3xl font-bold text-white">
                      {new Date(stats.date_range.latest).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">most recent article</div>
                  </div>
                )}
              </div>
              <div className="space-y-2">
                {Object.entries(stats.by_source)
                  .sort(([, a], [, b]) => b - a)
                  .map(([source, count]) => (
                    <div key={source} className="flex items-center gap-3">
                      <span className="text-sm text-gray-400 w-40 shrink-0">{source}</span>
                      <div className="flex-1 h-1.5 rounded-full bg-gray-800">
                        <div
                          className="h-full rounded-full bg-gray-600"
                          style={{ width: `${Math.round((count / stats.total) * 100)}%` }}
                        />
                      </div>
                      <span className="text-sm font-mono text-gray-500 w-10 text-right">{count}</span>
                    </div>
                  ))}
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-5 text-sm text-gray-500">
              Loading corpus stats…
            </div>
          )}
        </section>

        {/* RAGAS scorecard */}
        <section className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Model scorecard</h2>
            <p className="text-sm text-gray-400 mt-1">
              Evaluated with{" "}
              <a href="https://docs.ragas.io" className="underline hover:text-gray-200">RAGAS</a>
              {" "}(Es et al., arXiv:2309.15217) on {scorecard?.scores?.n_pairs ?? "—"} synthetic QA pairs
              generated from held-out articles.
            </p>
          </div>
          {scorecard?.available && scorecard.scores ? (
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-5 space-y-5">
              <MetricBar
                label="Faithfulness"
                value={scorecard.scores.faithfulness}
                description="Does the answer contain only claims supported by the retrieved sources? Measures hallucination rate."
              />
              <MetricBar
                label="Answer Relevancy"
                value={scorecard.scores.answer_relevancy}
                description="Does the answer actually address the question asked?"
              />
              <MetricBar
                label="Context Precision"
                value={scorecard.scores.context_precision}
                description="Are the retrieved chunks relevant to the question? Measures retrieval precision."
              />
              <MetricBar
                label="Context Recall"
                value={scorecard.scores.context_recall}
                description="Do the retrieved chunks cover the information needed to answer correctly?"
              />
            </div>
          ) : (
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-5 text-sm text-gray-500">
              {scorecard?.message ?? "Loading scorecard…"}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
