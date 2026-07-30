import { useEffect, useState } from 'react';
import { searchApi } from '../services/searchApi';
import type { SearchHistoryEntry } from '../types/search';
import { Clock, CheckCircle, XCircle } from 'lucide-react';

export default function SearchHistory() {
  const [history, setHistory] = useState<SearchHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    searchApi.getHistory()
      .then(res => { setHistory(res.history); setLoading(false); })
      .catch(err => { console.error(err); setLoading(false); });
  }, []);

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="heading-1">Search History</h1>
          <p className="text-muted" style={{ marginTop: 4 }}>Past retrieval sessions and their performance</p>
        </div>
      </div>

      <div className="table-container">
        {loading ? (
          <div className="empty-state">Loading history...</div>
        ) : history.length === 0 ? (
          <div className="empty-state">No history found. Run a search to see results here.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Query</th>
                <th>Modalities</th>
                <th>Latency</th>
                <th>Results</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {history.map(entry => (
                <tr key={entry.session_id}>
                  <td style={{ color: 'var(--text-3)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                    {new Date(entry.timestamp).toLocaleString()}
                  </td>
                  <td style={{ fontWeight: 500, maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {entry.query}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {entry.modalities.map(m => (
                        <span key={m} className="badge" style={{ textTransform: 'capitalize' }}>{m}</span>
                      ))}
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-2)' }}>
                      <Clock size={11} color="var(--text-3)" />
                      {entry.latency}ms
                    </div>
                  </td>
                  <td style={{ fontSize: 13, fontFamily: 'var(--font-mono)', color: 'var(--text-2)' }}>
                    {entry.results_count}
                  </td>
                  <td>
                    {entry.status === 'completed' ? (
                      <span className="badge badge-success">
                        <CheckCircle size={11} /> Completed
                      </span>
                    ) : (
                      <span className="badge badge-danger">
                        <XCircle size={11} /> Failed
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
