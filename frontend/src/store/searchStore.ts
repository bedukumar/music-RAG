import { create } from 'zustand';
import { RetrievalStage, type SearchResult, type PipelineStageState, type Modality } from '../types/search';

interface SearchSettings {
  defaultTopK: number;
  defaultFusionStrategy: string;
  defaultSearchMode: string;
  enableReranking: boolean;
  autoExpandResults: boolean;
  developerMode: boolean;
}

interface SearchState {
  // Query state
  query: string;
  modalities: Modality[];
  filters: {
    artist?: string;
    album?: string;
    genre?: string;
    year?: string;
    duration?: string;
    tags?: string[];
  };
  top_k: number;
  score_threshold: number;
  include_similarity_score: boolean;
  fusion_strategy: string;
  rerank: boolean;
  search_mode: string;

  // Execution state
  isSearching: boolean;
  pipelineState: Record<RetrievalStage, PipelineStageState>;
  
  // Results
  results: SearchResult[];
  selectedResults: string[]; // media_ids for comparison
  sessionId: string | null;
  overallLatency: number;

  // Settings
  settings: SearchSettings;

  // Actions
  setQuery: (q: string) => void;
  setModalities: (mods: Modality[]) => void;
  setTopK: (k: number) => void;
  setScoreThreshold: (t: number) => void;
  setIncludeSimilarityScore: (i: boolean) => void;
  setFusionStrategy: (strategy: string) => void;
  setRerank: (rerank: boolean) => void;
  setSearchMode: (mode: string) => void;
  setFilters: (filters: any) => void;
  
  startSearch: () => void;
  endSearch: (results: SearchResult[], sessionId: string, latency: number) => void;
  failSearch: (error: string) => void;
  
  updatePipelineStage: (stage: RetrievalStage, status: PipelineStageState['status'], latency_ms?: number) => void;
  resetPipeline: () => void;
  
  toggleResultSelection: (mediaId: string) => void;
  updateSettings: (settings: Partial<SearchSettings>) => void;
}

const defaultPipeline = () => {
  const stages = {} as Record<RetrievalStage, PipelineStageState>;
  Object.values(RetrievalStage).forEach(s => {
    stages[s] = { status: 'pending' };
  });
  return stages;
};

export const useSearchStore = create<SearchState>((set) => ({
  query: '',
  modalities: ['audio', 'transcript', 'metadata'],
  filters: {},
  top_k: 10,
  score_threshold: 0.0,
  include_similarity_score: true,
  fusion_strategy: 'rrf',
  rerank: false,
  search_mode: 'hybrid',

  isSearching: false,
  pipelineState: defaultPipeline(),
  
  results: [],
  selectedResults: [],
  sessionId: null,
  overallLatency: 0,

  settings: {
    defaultTopK: 10,
    defaultFusionStrategy: 'rrf',
    defaultSearchMode: 'hybrid',
    enableReranking: false,
    autoExpandResults: false,
    developerMode: false,
  },

  setQuery: (q) => set({ query: q }),
  setModalities: (mods) => set({ modalities: mods }),
  setTopK: (k) => set({ top_k: k }),
  setScoreThreshold: (t) => set({ score_threshold: t }),
  setIncludeSimilarityScore: (i) => set({ include_similarity_score: i }),
  setFusionStrategy: (s) => set({ fusion_strategy: s }),
  setRerank: (r) => set({ rerank: r }),
  setSearchMode: (m) => set({ search_mode: m }),
  setFilters: (f) => set((state) => ({ filters: { ...state.filters, ...f } })),

  startSearch: () => set({ 
    isSearching: true, 
    results: [], 
    sessionId: null, 
    pipelineState: defaultPipeline() 
  }),
  
  endSearch: (results, sessionId, latency) => set({ 
    isSearching: false, 
    results, 
    sessionId, 
    overallLatency: latency 
  }),
  
  failSearch: (_error) => set({ isSearching: false }), // In real app, might save error state

  updatePipelineStage: (stage, status, latency_ms) => set((state) => ({
    pipelineState: {
      ...state.pipelineState,
      [stage]: { status, latency_ms: latency_ms ?? state.pipelineState[stage].latency_ms }
    }
  })),
  
  resetPipeline: () => set({ pipelineState: defaultPipeline() }),

  toggleResultSelection: (mediaId) => set((state) => {
    const isSelected = state.selectedResults.includes(mediaId);
    return {
      selectedResults: isSelected 
        ? state.selectedResults.filter(id => id !== mediaId)
        : [...state.selectedResults, mediaId]
    };
  }),

  updateSettings: (s) => set((state) => ({ settings: { ...state.settings, ...s } }))
}));
