import { useSearchStore } from '../../store/searchStore';
import { Terminal } from 'lucide-react';

export default function DebugPanel() {
  const {
    settings, query, filters, modalities, top_k,
    fusion_strategy, rerank, sessionId, overallLatency, pipelineState,
  } = useSearchStore();

  if (!settings.developerMode) return null;

  return (
    <div
      style={{
        marginTop: 24,
        background: 'var(--bg-1)',
        border: '1px solid var(--border-2)',
        borderRadius: 'var(--r-3)',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '10px 16px',
          borderBottom: '1px solid var(--border-1)',
          background: 'var(--bg-app)',
        }}
      >
        <Terminal size={13} color="var(--text-3)" />
        <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>
          retrieval debugger
        </span>
      </div>

      {/* Code area */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 0,
        }}
      >
        <div style={{ padding: '12px 16px', borderRight: '1px solid var(--border-1)' }}>
          <p style={{ fontSize: 10, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>Query State</p>
          <pre className="code-block" style={{ margin: 0 }}>
            {JSON.stringify({ query, modalities, filters, top_k, fusion_strategy, rerank }, null, 2)}
          </pre>
        </div>
        <div style={{ padding: '12px 16px' }}>
          <p style={{ fontSize: 10, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>Session & Latency</p>
          <pre className="code-block" style={{ margin: 0 }}>
            {JSON.stringify({ sessionId, overallLatency, pipelineState }, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
