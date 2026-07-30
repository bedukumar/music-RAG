import api from '../api/client';
import type { SearchSessionResponse, SearchHistoryEntry, SearchAnalytics } from '../types/search';

export interface SearchRequestPayload {
  query: string;
  modalities: string[];
  filters?: Record<string, any>;
  tag_matches?: string[];
  top_k: number;
  score_threshold?: number;
  include_similarity_score?: boolean;
  rerank: boolean;
  fusion_strategy: string;
}

export const searchApi = {
  executeSearch: async (payload: SearchRequestPayload): Promise<SearchSessionResponse> => {
    const response = await api.post('/search', payload);
    return response.data;
  },

  getHistory: async (): Promise<{ history: SearchHistoryEntry[], count: number }> => {
    const response = await api.get('/search/history');
    return response.data;
  },

  getAnalytics: async (): Promise<SearchAnalytics> => {
    const response = await api.get('/search/analytics');
    return response.data;
  }
};
