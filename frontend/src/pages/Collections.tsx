import { useState, useEffect } from 'react';
import { CollectionsAPI } from '../api/client';
import { Database, Zap, Trash2, RefreshCw } from 'lucide-react';

export default function Collections() {
  const [collections, setCollections] = useState<any[]>([]);
  const [isProcessing, setIsProcessing] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);

  const loadCollections = () => {
    setLoading(true);
    CollectionsAPI.list()
      .then(res => {
        if (res.collections)               setCollections(res.collections);
        else if (Array.isArray(res))       setCollections(res);
        else if (typeof res === 'object')  setCollections(Object.keys(res).map(k => ({ name: k, ...res[k] })));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadCollections(); }, []);

  const handleOptimize = async (name: string) => {
    try {
      setIsProcessing(prev => ({ ...prev, [name]: true }));
      await CollectionsAPI.optimize(name);
      loadCollections();
    } catch (e) {
      console.error(e);
    } finally {
      setIsProcessing(prev => ({ ...prev, [name]: false }));
    }
  };

  const handleDelete = async (name: string) => {
    if (!window.confirm(`Drop collection "${name}"? This cannot be undone.`)) return;
    try {
      setIsProcessing(prev => ({ ...prev, [name]: true }));
      await CollectionsAPI.delete(name, true);
      loadCollections();
    } catch (e) {
      console.error(e);
    } finally {
      setIsProcessing(prev => ({ ...prev, [name]: false }));
    }
  };

  function statusBadge(status: string) {
    if (status === 'green')  return <span className="badge badge-success">Healthy</span>;
    if (status === 'yellow') return <span className="badge badge-warning">Degraded</span>;
    return <span className="badge badge-danger">{(status || 'unknown').toUpperCase()}</span>;
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="heading-1">Collections</h1>
          <p className="text-muted" style={{ marginTop: 4 }}>Vector database indices and embedding namespaces</p>
        </div>
        <button className="btn btn-secondary" onClick={loadCollections}>
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="empty-state">Loading collections...</div>
      ) : collections.length === 0 ? (
        <div className="empty-state">
          <Database size={24} color="var(--text-3)" />
          <p>No collections found.</p>
          <p style={{ fontSize: 12 }}>Collections appear after ingestion completes.</p>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {collections.map((col, idx) => (
            <div
              key={idx}
              style={{
                background: 'var(--bg-1)',
                border: '1px solid var(--border-1)',
                borderRadius: 'var(--r-3)',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: 16,
              }}
            >
              {/* Collection name */}
              <div className="flex items-center gap-3">
                <Database size={15} color="var(--text-3)" />
                <span style={{ fontWeight: 600, fontSize: 14, letterSpacing: '-0.01em', color: 'var(--text-1)' }}>
                  {col.name || 'Unnamed'}
                </span>
              </div>

              {/* Stats */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div className="flex items-center justify-between">
                  <span style={{ fontSize: 12, color: 'var(--text-3)' }}>Status</span>
                  {statusBadge(col.status || '')}
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ fontSize: 12, color: 'var(--text-3)' }}>Vectors</span>
                  <span style={{ fontSize: 13, fontWeight: 500, fontFamily: 'var(--font-mono)' }}>
                    {col.vectors_count !== undefined ? col.vectors_count.toLocaleString() : (col.count || 0)}
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div
                style={{
                  display: 'flex',
                  gap: 8,
                  paddingTop: 12,
                  borderTop: '1px solid var(--border-1)',
                }}
              >
                <button
                  className="btn btn-secondary"
                  style={{ flex: 1, fontSize: 12 }}
                  onClick={() => handleOptimize(col.name)}
                  disabled={isProcessing[col.name]}
                >
                  {isProcessing[col.name]
                    ? <><RefreshCw size={12} className="spin" /> Running</>
                    : <><Zap size={12} /> Optimize</>
                  }
                </button>
                <button
                  className="btn btn-danger"
                  style={{ width: 32, padding: 0 }}
                  onClick={() => handleDelete(col.name)}
                  disabled={isProcessing[col.name]}
                  title="Drop collection"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
