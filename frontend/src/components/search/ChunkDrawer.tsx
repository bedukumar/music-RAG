import type { RetrievedChunk } from '../../types/search';
import { Music, FileText, Tag, Clock } from 'lucide-react';

const MODALITY_COLORS: Record<string, string> = {
  audio:      'var(--accent)',
  transcript: 'var(--success)',
  metadata:   'var(--warning)',
};

function ModalityIcon({ modality }: { modality: string }) {
  const color = MODALITY_COLORS[modality] || 'var(--text-3)';
  if (modality === 'audio')      return <Music     size={13} color={color} />;
  if (modality === 'transcript') return <FileText  size={13} color={color} />;
  if (modality === 'metadata')   return <Tag       size={13} color={color} />;
  return null;
}

export default function ChunkDrawer({ chunks }: { chunks: RetrievedChunk[] }) {
  return (
    <div>
      <p style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
        Matched Chunks ({chunks.length})
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {chunks.map(chunk => (
          <div
            key={chunk.chunk_id}
            style={{
              padding: '10px 12px',
              background: 'var(--bg-1)',
              border: '1px solid var(--border-1)',
              borderRadius: 'var(--r-2)',
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            {/* Chunk header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <ModalityIcon modality={chunk.modality} />
                <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'capitalize', color: MODALITY_COLORS[chunk.modality] || 'var(--text-2)' }}>
                  {chunk.modality}
                </span>
                <span style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                  {chunk.chunk_id.substring(0, 8)}
                </span>
              </div>
              <span className="badge badge-accent" style={{ fontFamily: 'var(--font-mono)' }}>
                {chunk.score.toFixed(4)}
              </span>
            </div>

            {/* Timestamps */}
            {chunk.timestamps && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-3)', fontSize: 11 }}>
                <Clock size={11} />
                <span style={{ fontFamily: 'var(--font-mono)' }}>
                  {chunk.timestamps[0].toFixed(1)}s – {chunk.timestamps[1].toFixed(1)}s
                </span>
              </div>
            )}

            {/* Content */}
            {chunk.content && (
              <p style={{ fontSize: 12, lineHeight: 1.6, color: 'var(--text-2)', fontFamily: chunk.modality === 'metadata' ? 'var(--font-mono)' : 'var(--font)' }}>
                {chunk.content}
              </p>
            )}

            {/* Audio placeholder */}
            {chunk.modality === 'audio' && !chunk.content && (
              <div
                style={{
                  height: 32,
                  background: 'var(--bg-3)',
                  borderRadius: 'var(--r-1)',
                  display: 'flex',
                  alignItems: 'center',
                  paddingLeft: 12,
                  color: 'var(--text-3)',
                  fontSize: 11,
                  fontStyle: 'italic',
                }}
              >
                Audio segment — no transcript available
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
