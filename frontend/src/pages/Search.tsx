import { useEffect } from 'react';
import SearchBar from '../components/search/SearchBar';
import SearchConfiguration from '../components/search/SearchConfiguration';
import PipelineVisualizer from '../components/search/PipelineVisualizer';
import SearchResults from '../components/search/SearchResults';
import DebugPanel from '../components/search/DebugPanel';
import { useSearchStore } from '../store/searchStore';
import { searchApi } from '../services/searchApi';
import { useSearchWebsocket } from '../hooks/useSearchWebsocket';

export default function Search() {
  useSearchWebsocket();
  const {
    query, modalities, filters, top_k, rerank, fusion_strategy,
    isSearching, endSearch, failSearch,
  } = useSearchStore();

  useEffect(() => {
    let mounted = true;

    async function performSearch() {
      if (!isSearching) return;
      try {
        const payload = {
          query,
          modalities,
          filters: { ...filters, tags: undefined },
          tag_matches: filters.tags || [],
          top_k,
          score_threshold: useSearchStore.getState().score_threshold,
          include_similarity_score: useSearchStore.getState().include_similarity_score,
          rerank,
          fusion_strategy,
        };
        const res = await searchApi.executeSearch(payload);
        if (mounted) {
          const overallLatency = Object.values(res.latency_ms || {}).reduce((a, b) => a + b, 0) || 0;
          endSearch(res.results, res.session_id, overallLatency);
        }
      } catch (err: any) {
        if (mounted) failSearch(err.message || 'Search failed');
      }
    }

    performSearch();
    return () => { mounted = false; };
  }, [isSearching]);

  return (
    <div className="animate-fade-in">
      {/* Page header */}
      <div className="page-header">
        <div>
          <h1 className="heading-1">Search</h1>
          <p className="text-muted" style={{ marginTop: 4 }}>
            Multi-modal retrieval across audio, transcripts, and metadata
          </p>
        </div>
      </div>

      {/* Search bar */}
      <SearchBar />

      {/* Config (inline below search) */}
      <div style={{ marginTop: 16 }}>
        <SearchConfiguration />
      </div>

      {/* Pipeline status — only shows while searching or after */}
      <div style={{ marginTop: 24 }}>
        <PipelineVisualizer />
      </div>

      {/* Results */}
      <div style={{ marginTop: 24 }}>
        <SearchResults />
      </div>

      {/* Debug panel */}
      <DebugPanel />
    </div>
  );
}
