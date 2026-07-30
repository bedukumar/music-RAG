import { useState } from 'react';
import type { SearchResult } from '../../types/search';
import { ChevronDown, ChevronRight, Music, FileText, Tag, PlayCircle } from 'lucide-react';
import ChunkDrawer from './ChunkDrawer';
import { useSearchStore } from '../../store/searchStore';

export default function ResultCard({ result, rank }: { result: SearchResult; rank: number }) {
  const [expanded, setExpanded] = useState(false);
  const { toggleResultSelection, selectedResults } = useSearchStore();

  const isSelected       = selectedResults.includes(result?.media_id);
  const hasAudio         = result.matched_chunks.some(c => c.modality === 'audio');
  const hasTranscript    = result.matched_chunks.some(c => c.modality === 'transcript');
  const hasMetadata      = result.matched_chunks.some(c => c.modality === 'metadata');

  return (
    <div
      style={{
        background: 'var(--bg-1)',
        border: '1px solid',
        borderColor: isSelected ? 'var(--accent-border)' : 'var(--border-1)',
        borderRadius: 'var(--r-3)',
        transition: 'border-color var(--t-fast)',
        overflow: 'hidden',
      }}
    >
      {/* Main row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '32px 1fr auto',
          alignItems: 'center',
          gap: 0,
          padding: '12px 16px',
        }}
      >
        {/* Rank */}
        <span
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: 'var(--text-3)',
            fontFamily: 'var(--font-mono)',
            userSelect: 'none',
          }}
        >
          {rank}
        </span>

        {/* Content */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Thumbnail placeholder */}
          <div
            style={{
              width: 40,
              height: 40,
              flexShrink: 0,
              background: 'var(--bg-3)',
              borderRadius: 'var(--r-2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {hasAudio
              ? <PlayCircle size={16} color="var(--text-3)" />
              : <Music size={16} color="var(--text-3)" />
            }
          </div>

          {/* Title + meta */}
          <div style={{ minWidth: 0 }}>
            <div
              style={{
                fontSize: 14,
                fontWeight: 500,
                color: 'var(--text-1)',
                letterSpacing: '-0.01em',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {result.title}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 3 }}>
              <span style={{ fontSize: 12, color: 'var(--text-3)' }}>
                {result.metadata?.artist || 'Unknown Artist'}
                {result.metadata?.album ? ` — ${result.metadata.album}` : ''}
              </span>
            </div>
          </div>

          {/* Badges */}
          <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginLeft: 8, flexShrink: 0 }}>
            <span className="badge badge-accent">
              {result.overall_score.toFixed(3)}
            </span>
            {hasAudio      && <span className="badge"><Music     size={10} style={{ marginRight: 2 }} />Audio</span>}
            {hasTranscript && <span className="badge"><FileText  size={10} style={{ marginRight: 2 }} />Transcript</span>}
            {hasMetadata   && <span className="badge"><Tag       size={10} style={{ marginRight: 2 }} />Metadata</span>}
            <span className="badge">{result.matched_chunks.length} chunks</span>
          </div>
        </div>

        {/* Trailing controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 16 }}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => toggleResultSelection(result.media_id)}
            style={{ cursor: 'pointer' }}
          />
          <button
            className="btn-icon"
            onClick={() => setExpanded(!expanded)}
            style={{ border: 'none' }}
            title={expanded ? 'Collapse' : 'Expand chunks'}
          >
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        </div>
      </div>

      {/* Expanded chunk drawer */}
      {expanded && (
        <div
          style={{
            borderTop: '1px solid var(--border-1)',
            padding: '16px',
            background: 'var(--bg-app)',
          }}
        >
          <ChunkDrawer chunks={result.matched_chunks} />
        </div>
      )}
    </div>
  );
}
