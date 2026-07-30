import { useState } from 'react';
import { Save, RefreshCw, AlertTriangle, CheckCircle } from 'lucide-react';

export default function Settings() {
  const [isRecovering, setIsRecovering] = useState(false);
  const [recoveryResult, setRecoveryResult] = useState<any>(null);

  const handleRecover = async () => {
    if (!confirm('Scan the vector database and recover missing local records. Proceed?')) return;
    setIsRecovering(true);
    setRecoveryResult(null);
    try {
      const res = await fetch('/api/v1/system/recover', { method: 'POST' });
      const data = await res.json();
      setRecoveryResult({ success: true, data });
    } catch (e: any) {
      setRecoveryResult({ success: false, error: e.message });
    } finally {
      setIsRecovering(false);
    }
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="heading-1">Settings</h1>
          <p className="text-muted" style={{ marginTop: 4 }}>System configuration and maintenance</p>
        </div>
      </div>

      <div style={{ maxWidth: 680, display: 'flex', flexDirection: 'column', gap: 24 }}>

        {/* General settings */}
        <section>
          <h2 className="heading-2" style={{ marginBottom: 16 }}>General</h2>
          <div
            style={{
              background: 'var(--bg-1)',
              border: '1px solid var(--border-1)',
              borderRadius: 'var(--r-3)',
              overflow: 'hidden',
            }}
          >
            {/* Qdrant URL row */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '200px 1fr',
                alignItems: 'center',
                gap: 24,
                padding: '14px 20px',
                borderBottom: '1px solid var(--border-1)',
              }}
            >
              <div>
                <p style={{ fontSize: 13, fontWeight: 500 }}>Qdrant URL</p>
                <p style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>Vector database endpoint</p>
              </div>
              <input
                type="text"
                className="input"
                defaultValue="http://localhost:6333"
                disabled
                style={{ maxWidth: 300 }}
              />
            </div>

            {/* Embedding model row */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '200px 1fr',
                alignItems: 'center',
                gap: 24,
                padding: '14px 20px',
              }}
            >
              <div>
                <p style={{ fontSize: 13, fontWeight: 500 }}>Embedding Model</p>
                <p style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>Managed via environment</p>
              </div>
              <select className="input" disabled style={{ maxWidth: 300 }}>
                <option>default-mock-model (v1)</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}>
            <button className="btn btn-secondary" disabled>
              <Save size={13} />
              Save Changes
            </button>
          </div>
        </section>

        {/* System maintenance */}
        <section>
          <h2 className="heading-2" style={{ marginBottom: 16 }}>System Maintenance</h2>
          <div
            style={{
              background: 'var(--bg-1)',
              border: '1px solid var(--border-1)',
              borderRadius: 'var(--r-3)',
              overflow: 'hidden',
            }}
          >
            <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Warning callout */}
              <div
                style={{
                  display: 'flex',
                  gap: 12,
                  padding: '12px 14px',
                  background: 'var(--warning-bg)',
                  border: '1px solid rgba(245, 158, 11, 0.15)',
                  borderRadius: 'var(--r-2)',
                }}
              >
                <AlertTriangle size={15} color="var(--warning)" style={{ flexShrink: 0, marginTop: 1 }} />
                <div>
                  <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--warning)', marginBottom: 4 }}>Data Recovery</p>
                  <p style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.5 }}>
                    If your local database is lost or corrupted, scan the Qdrant vector store
                    to reconstruct media records automatically.
                  </p>
                </div>
              </div>

              <div>
                <button
                  className="btn btn-secondary"
                  onClick={handleRecover}
                  disabled={isRecovering}
                >
                  {isRecovering
                    ? <><RefreshCw size={13} className="spin" /> Scanning Qdrant...</>
                    : <><RefreshCw size={13} /> Run Recovery Scan</>
                  }
                </button>
              </div>

              {/* Recovery result */}
              {recoveryResult && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '10px 14px',
                    borderRadius: 'var(--r-2)',
                    fontSize: 13,
                    background: recoveryResult.success ? 'var(--success-bg)' : 'var(--danger-bg)',
                    border: `1px solid ${recoveryResult.success ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)'}`,
                    color: recoveryResult.success ? 'var(--success)' : 'var(--danger)',
                  }}
                >
                  <CheckCircle size={14} />
                  {recoveryResult.success
                    ? `Recovered ${recoveryResult.data.recovered_items} items successfully.`
                    : `Recovery failed: ${recoveryResult.error}`
                  }
                </div>
              )}
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}
