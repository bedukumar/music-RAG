import { useSearchStore } from '../../store/searchStore';
import ResultCard from './ResultCard';

export default function SearchResults() {
  const { results, isSearching, overallLatency } = useSearchStore();

  if (isSearching) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {[1, 2, 3].map(i => (
          <div
            key={i}
            className="skeleton"
            style={{
              height: 80,
              borderRadius: 'var(--r-3)',
              opacity: 1 - (i - 1) * 0.2,
            }}
          />
        ))}
      </div>
    );
  }

  if (results.length === 0) return null;

  return (
    <div>
      {/* Results header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 12,
        }}
      >
        <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-1)' }}>
          {results.length} result{results.length !== 1 ? 's' : ''}
        </p>
        {overallLatency > 0 && (
          <span style={{ fontSize: 12, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
            {overallLatency.toFixed(0)}ms
          </span>
        )}
      </div>

      {/* Result list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {results.map((result, idx) => (
          <ResultCard
            key={`${result.media.media_id}-${idx}`}
            result={result}
            rank={idx + 1}
          />
        ))}
      </div>
    </div>
  );
}
