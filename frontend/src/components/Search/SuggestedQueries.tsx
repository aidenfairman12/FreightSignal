"use client";

interface Props {
  queries: string[];
  onSelect: (query: string) => void;
}

export default function SuggestedQueries({ queries, onSelect }: Props) {
  return (
    <div className="mt-8">
      <p className="text-xs font-semibold uppercase tracking-widest text-gray-600 mb-3">
        Try asking
      </p>
      <div className="flex flex-wrap gap-2">
        {queries.map((q) => (
          <button
            key={q}
            onClick={() => onSelect(q)}
            className="rounded-full border border-gray-800 bg-gray-900 px-4 py-2 text-sm text-gray-400 hover:border-emerald-500/40 hover:text-emerald-400 transition-colors text-left"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
