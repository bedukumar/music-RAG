export type Modality = 'audio' | 'transcript' | 'metadata';

export interface SearchFilters {
  exact_matches: Record<string, any>;
  tag_matches: string[];
}

export interface SearchQuery {
  text: string;
  active_modalities: Modality[];
  filters: SearchFilters;
  top_k: number;
  rerank: boolean;
  fusion_strategy: string;
}

export interface RetrievedChunk {
  chunk_id: string;
  modality: Modality;
  score: number;
  content: string;
  timestamps?: [number, number];
}

export interface RetrievedMedia {
  media_id: string;
  title: string;
  media_type: string;
  metadata: Record<string, any>;
}

export interface SearchResult {
  media: RetrievedMedia;
  matched_chunks: RetrievedChunk[];
  overall_score: number;
}

export interface SearchSessionResponse {
  session_id: string;
  latency_ms: Record<string, number>;
  results: SearchResult[];
}

export interface SearchHistoryEntry {
  session_id: string;
  query: string;
  modalities: string[];
  top_k: number;
  fusion_strategy: string;
  latency: number;
  results_count: number;
  timestamp: string;
  status: 'completed' | 'failed';
}

export interface SearchAnalytics {
  total_searches: number;
  avg_latency: number;
  avg_retrieval_time: number;
  avg_rerank_time: number;
  most_used_modality: string;
  most_used_fusion: string;
  success_rate: number;
  searches_per_day: { date: string; count: number }[];
  latency_trend: { date: string; latency: number }[];
  top_artists: { name: string; count: number }[];
  top_genres: { name: string; count: number }[];
  modality_distribution: { name: string; value: number }[];
  fusion_distribution: { name: string; value: number }[];
}

export const RetrievalStage = {
  VALIDATION: 'validation',
  QUERY_NORMALIZATION: 'query_normalization',
  QUERY_EXPANSION: 'query_expansion',
  MODALITY_SELECTION: 'modality_selection',
  EMBEDDING_GENERATION: 'embedding_generation',
  VECTOR_RETRIEVAL: 'vector_retrieval',
  PAYLOAD_LOADING: 'payload_loading',
  RESULT_FUSION: 'result_fusion',
  RERANKING: 'reranking',
  POST_PROCESSING: 'post_processing',
  RESPONSE_BUILDING: 'response_building',
} as const;

export type RetrievalStage = (typeof RetrievalStage)[keyof typeof RetrievalStage];

export interface PipelineStageState {
  status: 'pending' | 'running' | 'completed' | 'failed';
  latency_ms?: number;
}
