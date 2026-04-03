"use client";

import type { SourceResult } from "@/types";

interface Props {
  source: SourceResult;
  index: number;
}

function relevanceBar(score: number) {
  // Cross-encoder scores are roughly in [-10, 10]; clamp to [0, 1] for display
  const pct = Math.max(0, Math.min(1, (score + 5) / 10));
  const color =
    pct > 0.65 ? "bg-emerald-500" :
    pct > 0.4  ? "bg-yellow-500"  : "bg-gray-600";
  return { pct, color };
}

export default function SourceCard({ source, index }: Props) {
  const { pct, color } = relevanceBar(source.score);
  const date = source.published
    ? new Date(source.published).toLocaleDateString("en-US", {
        month: "short", day: "numeric", year: "numeric",
      })
    : "";

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 text-sm">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-white hover:text-emerald-400 transition-colors line-clamp-2"
          >
            {source.title || "Untitled"}
          </a>
          <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
            <span className="font-medium text-gray-400">{source.source}</span>
            {date && <><span>·</span><span>{date}</span></>}
          </div>
        </div>
        <span className="shrink-0 text-xs text-gray-600 font-mono">
          #{index + 1}
        </span>
      </div>

      {/* Relevance bar */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs text-gray-600 w-16 shrink-0">Relevance</span>
        <div className="flex-1 h-1.5 rounded-full bg-gray-800">
          <div
            className={`h-full rounded-full ${color} transition-all`}
            style={{ width: `${Math.round(pct * 100)}%` }}
          />
        </div>
        <span className="text-xs text-gray-600 font-mono w-10 text-right">
          {source.score.toFixed(2)}
        </span>
      </div>

      {/* Excerpt */}
      <p className="text-gray-400 leading-relaxed line-clamp-3">
        {source.text}
      </p>
    </div>
  );
}
