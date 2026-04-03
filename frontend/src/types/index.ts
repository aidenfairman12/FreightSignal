export interface SourceResult {
  text: string;
  title: string;
  source: string;
  url: string;
  published: string;
  score: number;
}

export interface QueryResponse {
  question: string;
  answer: string;
  sources: SourceResult[];
}

export interface CorpusStats {
  total: number;
  by_source: Record<string, number>;
  date_range: {
    earliest: string | null;
    latest: string | null;
  } | null;
}

export interface RagasScores {
  faithfulness: number;
  answer_relevancy: number;
  context_precision: number;
  context_recall: number;
  n_pairs: number;
}

export interface ScorecardResponse {
  available: boolean;
  message?: string;
  scores: RagasScores | null;
}
