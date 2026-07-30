import React from 'react';
import { useSearchStore } from '../../store/searchStore';
import { RetrievalStage, type PipelineStageState } from '../../types/search';
import { CheckCircle, Circle, Loader2, XCircle } from 'lucide-react';

const STAGES: { key: RetrievalStage; label: string }[] = [
  { key: RetrievalStage.VALIDATION,          label: 'Validate'  },
  { key: RetrievalStage.QUERY_NORMALIZATION, label: 'Normalize' },
  { key: RetrievalStage.EMBEDDING_GENERATION,label: 'Embed'     },
  { key: RetrievalStage.VECTOR_RETRIEVAL,    label: 'Retrieve'  },
  { key: RetrievalStage.RESULT_FUSION,       label: 'Fuse'      },
  { key: RetrievalStage.RERANKING,           label: 'Rerank'    },
  { key: RetrievalStage.RESPONSE_BUILDING,   label: 'Build'     },
];

function StageIndicator({ state }: { state: PipelineStageState }) {
  if (state.status === 'completed') return <CheckCircle size={12} color="var(--success)" />;
  if (state.status === 'failed')    return <XCircle     size={12} color="var(--danger)" />;
  if (state.status === 'running')   return <Loader2     size={12} color="var(--accent)" className="spin" />;
  return <Circle size={12} color="var(--text-3)" />;
}

export default function PipelineVisualizer() {
  const { pipelineState, isSearching, overallLatency } = useSearchStore();

  // Only show when a search is active or complete
  const hasActivity = isSearching || Object.values(pipelineState).some(s => s.status !== 'pending');
  if (!hasActivity) return null;

  return (
    <div
      style={{
        background: 'var(--bg-1)',
        border: '1px solid var(--border-1)',
        borderRadius: 'var(--r-3)',
        padding: '12px 16px',
        overflowX: 'auto',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 0,
          minWidth: 600,
        }}
      >
        {STAGES.map((stage, idx) => {
          const state = pipelineState[stage.key] || { status: 'pending' };
          const isActive = state.status === 'running';
          const isDone   = state.status === 'completed';

          return (
            <React.Fragment key={stage.key}>
              {/* Stage node */}
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 4,
                  minWidth: 72,
                  flexShrink: 0,
                }}
              >
                <StageIndicator state={state} />
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: isActive ? 600 : 400,
                    color: isDone ? 'var(--text-2)' : isActive ? 'var(--text-1)' : 'var(--text-3)',
                    textAlign: 'center',
                    letterSpacing: '-0.01em',
                  }}
                >
                  {stage.label}
                </span>
                {state.latency_ms !== undefined && (
                  <span style={{ fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                    {state.latency_ms.toFixed(0)}ms
                  </span>
                )}
              </div>

              {/* Connector line */}
              {idx < STAGES.length - 1 && (
                <div
                  style={{
                    flex: 1,
                    height: 1,
                    background: isDone ? 'var(--border-3)' : 'var(--border-1)',
                    marginBottom: 18,
                    transition: 'background var(--t-normal)',
                  }}
                />
              )}
            </React.Fragment>
          );
        })}

        {/* Total latency */}
        {overallLatency > 0 && !isSearching && (
          <span
            style={{
              marginLeft: 16,
              fontSize: 11,
              color: 'var(--text-3)',
              fontFamily: 'var(--font-mono)',
              whiteSpace: 'nowrap',
              alignSelf: 'center',
              marginBottom: 18,
            }}
          >
            {overallLatency.toFixed(0)}ms total
          </span>
        )}
      </div>
    </div>
  );
}
