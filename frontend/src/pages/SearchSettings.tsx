import { useSearchStore } from '../store/searchStore';

type SettingRow = {
  label: string;
  description: string;
  key: 'developerMode' | 'autoExpandResults' | 'enableReranking';
};

const TOGGLE_SETTINGS: SettingRow[] = [
  { label: 'Developer Mode', description: 'Show retrieval debugger and execution traces.', key: 'developerMode' },
  { label: 'Auto-Expand Results', description: 'Automatically open the chunk drawer for all matches.', key: 'autoExpandResults' },
  { label: 'Enable Re-ranking', description: 'Enable cross-encoder re-ranking by default.', key: 'enableReranking' },
];

export default function SearchSettings() {
  const { settings, updateSettings } = useSearchStore();

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="heading-1">Search Settings</h1>
          <p className="text-muted" style={{ marginTop: 4 }}>Default behaviors and developer tools</p>
        </div>
      </div>

      <div style={{ maxWidth: 560, display: 'flex', flexDirection: 'column', gap: 24 }}>

        {/* Toggle settings */}
        <section>
          <h2 className="heading-2" style={{ marginBottom: 16 }}>Behavior</h2>
          <div
            style={{
              background: 'var(--bg-1)',
              border: '1px solid var(--border-1)',
              borderRadius: 'var(--r-3)',
              overflow: 'hidden',
            }}
          >
            {TOGGLE_SETTINGS.map((s, i) => (
              <div
                key={s.key}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '14px 20px',
                  borderBottom: i < TOGGLE_SETTINGS.length - 1 ? '1px solid var(--border-1)' : 'none',
                }}
              >
                <div>
                  <p style={{ fontSize: 13, fontWeight: 500 }}>{s.label}</p>
                  <p style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>{s.description}</p>
                </div>
                <label className="toggle-switch" style={{ marginLeft: 24 }}>
                  <input
                    type="checkbox"
                    checked={settings[s.key] as boolean}
                    onChange={e => updateSettings({ [s.key]: e.target.checked })}
                  />
                  <span className="toggle-slider" />
                </label>
              </div>
            ))}
          </div>
        </section>

        {/* Defaults */}
        <section>
          <h2 className="heading-2" style={{ marginBottom: 16 }}>Defaults</h2>
          <div
            style={{
              background: 'var(--bg-1)',
              border: '1px solid var(--border-1)',
              borderRadius: 'var(--r-3)',
              overflow: 'hidden',
            }}
          >
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
                <p style={{ fontSize: 13, fontWeight: 500 }}>Default Top K</p>
                <p style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>Number of results to retrieve</p>
              </div>
              <input
                type="number"
                value={settings.defaultTopK}
                onChange={e => updateSettings({ defaultTopK: parseInt(e.target.value) })}
                className="input-field"
                style={{ width: 88 }}
              />
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}
