import { useState } from 'react';
import { useSearchStore } from '../../store/searchStore';
import type { Modality } from '../../types/search';
import SearchFilters from './SearchFilters';
import { ChevronDown, ChevronUp } from 'lucide-react';

const MODALITIES: Modality[] = ['audio', 'transcript', 'metadata'];

export default function SearchConfiguration() {
  const {
    modalities, setModalities,
    top_k, setTopK,
    fusion_strategy, setFusionStrategy,
    rerank, setRerank,
    search_mode, setSearchMode,
  } = useSearchStore();
  const [showFilters, setShowFilters] = useState(false);

  const toggleModality = (m: Modality) => {
    if (modalities.includes(m)) setModalities(modalities.filter(x => x !== m));
    else setModalities([...modalities, m]);
  };

  const scoreThreshold = useSearchStore(s => s.score_threshold);
  const includeSimilarity = useSearchStore(s => s.include_similarity_score);

  return (
    <div
      style={{
        background: 'var(--bg-1)',
        border: '1px solid var(--border-1)',
        borderRadius: 'var(--r-3)',
        overflow: 'hidden',
      }}
    >
      {/* Main config row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'auto 1fr 1fr 1fr auto auto auto',
          gap: 0,
          alignItems: 'stretch',
          borderBottom: showFilters ? '1px solid var(--border-1)' : 'none',
        }}
      >
        {/* Modality toggles */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            padding: '8px 12px',
            borderRight: '1px solid var(--border-1)',
          }}
        >
          {MODALITIES.map(m => (
            <button
              key={m}
              type="button"
              onClick={() => toggleModality(m)}
              style={{
                height: 26,
                padding: '0 10px',
                borderRadius: 'var(--r-1)',
                border: '1px solid transparent',
                background: modalities.includes(m) ? 'var(--accent-bg)' : 'transparent',
                borderColor: modalities.includes(m) ? 'var(--accent-border)' : 'transparent',
                color: modalities.includes(m) ? 'var(--accent)' : 'var(--text-3)',
                fontFamily: 'var(--font)',
                fontSize: 12,
                fontWeight: 500,
                cursor: 'pointer',
                textTransform: 'capitalize',
                transition: 'all var(--t-fast)',
              }}
            >
              {m}
            </button>
          ))}
        </div>

        {/* Search mode */}
        <div style={{ padding: '8px 12px', borderRight: '1px solid var(--border-1)', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 10, color: 'var(--text-3)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Mode</label>
          <select
            value={search_mode}
            onChange={e => setSearchMode(e.target.value)}
            className="glass-select"
            style={{ height: 24, fontSize: 12, padding: '0 22px 0 8px' }}
          >
            <option value="semantic">Semantic</option>
            <option value="hybrid">Hybrid</option>
            <option value="metadata">Metadata</option>
          </select>
        </div>

        {/* Fusion strategy */}
        <div style={{ padding: '8px 12px', borderRight: '1px solid var(--border-1)', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 10, color: 'var(--text-3)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Fusion</label>
          <select
            value={fusion_strategy}
            onChange={e => setFusionStrategy(e.target.value)}
            className="glass-select"
            style={{ height: 24, fontSize: 12, padding: '0 22px 0 8px' }}
          >
            <option value="rrf">RRF</option>
            <option value="weighted">Weighted</option>
            <option value="max">Max Score</option>
            <option value="average">Average</option>
          </select>
        </div>

        {/* Top K slider */}
        <div style={{ padding: '8px 12px', borderRight: '1px solid var(--border-1)', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label style={{ fontSize: 10, color: 'var(--text-3)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Top K</label>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent)', fontFamily: 'var(--font-mono)' }}>{top_k}</span>
          </div>
          <input
            type="range" min="1" max="50"
            value={top_k}
            onChange={e => setTopK(parseInt(e.target.value))}
            className="range-slider"
          />
        </div>

        {/* Re-rank toggle */}
        <div style={{ padding: '8px 16px', borderRight: '1px solid var(--border-1)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
          <label style={{ fontSize: 10, color: 'var(--text-3)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>Re-rank</label>
          <label className="toggle-switch">
            <input type="checkbox" checked={rerank} onChange={e => setRerank(e.target.checked)} />
            <span className="toggle-slider" />
          </label>
        </div>

        {/* Scores toggle */}
        <div style={{ padding: '8px 16px', borderRight: '1px solid var(--border-1)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
          <label style={{ fontSize: 10, color: 'var(--text-3)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>Scores</label>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={includeSimilarity}
              onChange={e => useSearchStore.getState().setIncludeSimilarityScore(e.target.checked)}
            />
            <span className="toggle-slider" />
          </label>
        </div>

        {/* Filters toggle */}
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            padding: '0 14px',
            background: showFilters ? 'var(--bg-2)' : 'transparent',
            border: 'none',
            color: showFilters ? 'var(--text-1)' : 'var(--text-3)',
            cursor: 'pointer',
            fontSize: 12,
            fontFamily: 'var(--font)',
            fontWeight: 500,
            transition: 'all var(--t-fast)',
            whiteSpace: 'nowrap',
          }}
        >
          Filters
          {showFilters ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>
      </div>

      {/* Score threshold row (always visible, compact) */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          padding: '8px 16px',
          borderBottom: showFilters ? '1px solid var(--border-1)' : 'none',
        }}
      >
        <span style={{ fontSize: 10, color: 'var(--text-3)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>
          Min Score
        </span>
        <input
          type="range" min="0" max="1" step="0.05"
          value={scoreThreshold}
          onChange={e => useSearchStore.getState().setScoreThreshold(parseFloat(e.target.value))}
          className="range-slider"
          style={{ flex: 1 }}
        />
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-2)', fontFamily: 'var(--font-mono)', width: 32, textAlign: 'right' }}>
          {scoreThreshold.toFixed(2)}
        </span>
      </div>

      {/* Advanced filters (collapsible) */}
      {showFilters && (
        <div style={{ padding: '12px 16px' }}>
          <SearchFilters />
        </div>
      )}
    </div>
  );
}
