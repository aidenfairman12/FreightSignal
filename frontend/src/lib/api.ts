import type { CorpusStats, QueryResponse, ScorecardResponse } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function querySignal(
  question: string,
  nSources = 5
): Promise<QueryResponse> {
  return apiFetch<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify({ question, n_sources: nSources }),
  });
}

export async function fetchCorpusStats(): Promise<CorpusStats> {
  return apiFetch<CorpusStats>("/sources");
}

export async function fetchScorecard(): Promise<ScorecardResponse> {
  return apiFetch<ScorecardResponse>("/scorecard");
}
