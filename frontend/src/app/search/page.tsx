"use client";

import { useState } from "react";
import { querySignal } from "@/lib/api";
import type { QueryResponse } from "@/types";
import SourceCard from "@/components/Search/SourceCard";
import SuggestedQueries from "@/components/Search/SuggestedQueries";

const EXAMPLE_QUERIES = [
  "What's currently disrupting US port operations?",
  "How are rail strikes affecting freight shipments?",
  "What impact is the Panama Canal drought having on supply chains?",
  "Which commodities are seeing the biggest cost increases?",
  "What's happening with trucking capacity in the midwest?",
];

export default function SearchPage() {
  const [question, setQuestion]     = useState("");
  const [result, setResult]         = useState<QueryResponse | null>(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState<string | null>(null);

  async function handleSubmit(q?: string) {
    const query = (q ?? question).trim();
    if (!query) return;
    setQuestion(query);
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await querySignal(query);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-950 text-white">
      <div className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-2xl font-bold text-white mb-1">FreightSignal</h1>
        <p className="text-gray-400 text-sm mb-8">
          Ask anything about current supply chain disruptions. Answers are grounded in live logistics news.
        </p>

        {/* Search bar */}
        <form
          onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What's disrupting steel shipments right now?"
            className="flex-1 rounded-lg border border-gray-700 bg-gray-900 px-4 py-3 text-sm text-white placeholder-gray-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="rounded-lg bg-emerald-500 px-6 py-3 text-sm font-semibold text-gray-950 hover:bg-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "Searching…" : "Ask"}
          </button>
        </form>

        {/* Suggested queries */}
        {!result && !loading && (
          <SuggestedQueries queries={EXAMPLE_QUERIES} onSelect={handleSubmit} />
        )}

        {/* Error */}
        {error && (
          <div className="mt-6 rounded-lg border border-red-800 bg-red-900/20 p-4 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="mt-8 space-y-3 animate-pulse">
            <div className="h-4 rounded bg-gray-800 w-3/4" />
            <div className="h-4 rounded bg-gray-800 w-full" />
            <div className="h-4 rounded bg-gray-800 w-5/6" />
            <div className="h-4 rounded bg-gray-800 w-2/3" />
          </div>
        )}

        {/* Answer */}
        {result && (
          <div className="mt-8 space-y-8">
            {/* Answer block */}
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-widest text-emerald-400 mb-3">
                Answer
              </h2>
              <div className="rounded-lg border border-gray-800 bg-gray-900 p-5 text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
                {result.answer}
              </div>
            </div>

            {/* Sources */}
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-3">
                {result.sources.length} source{result.sources.length !== 1 ? "s" : ""} retrieved
              </h2>
              <div className="space-y-3">
                {result.sources.map((source, i) => (
                  <SourceCard key={i} source={source} index={i} />
                ))}
              </div>
            </div>

            {/* New question */}
            <button
              onClick={() => { setResult(null); setQuestion(""); }}
              className="text-sm text-gray-500 hover:text-gray-300 underline transition-colors"
            >
              ← Ask another question
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
