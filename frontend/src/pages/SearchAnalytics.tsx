import { useEffect, useState } from 'react';
import { searchApi } from '../services/searchApi';
import type { SearchAnalytics as SearchAnalyticsType } from '../types/search';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line,
} from 'recharts';

const CHART_STYLE = {
  background: 'var(--bg-1)',
  border: '1px solid var(--border-1)',
  borderRadius: 5,
  fontSize: 11,
  color: 'var(--text-2)',
};

export default function SearchAnalytics() {
  const [analytics, setAnalytics] = useState<SearchAnalyticsType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    searchApi.getAnalytics()
      .then(res => { setAnalytics(res); setLoading(false); })
      .catch(err => { console.error(err); setLoading(false); });
  }, []);

  if (loading) return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="heading-1">Analytics</h1>
      </div>
      <div className="empty-state">Loading analytics...</div>
    </div>
  );

  if (!analytics) return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="heading-1">Analytics</h1>
      </div>
      <div className="empty-state">Failed to load analytics.</div>
    </div>
  );

  const stats = [
    { label: 'Total Searches', value: analytics.total_searches },
    { label: 'Avg Latency',    value: `${analytics.avg_latency}ms` },
    { label: 'Success Rate',   value: `${(analytics.success_rate * 100).toFixed(1)}%` },
    { label: 'Top Modality',   value: analytics.most_used_modality },
  ];

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="heading-1">Analytics</h1>
          <p className="text-muted" style={{ marginTop: 4 }}>Retrieval performance metrics and usage trends</p>
        </div>
      </div>

      {/* Stat row */}
      <div className="grid grid-cols-4 gap-4" style={{ marginBottom: 32 }}>
        {stats.map(s => (
          <div key={s.label} className="stat-card">
            <div className="stat-label">{s.label}</div>
            <div className="stat-value" style={{ fontSize: 22 }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-4">
        {/* Latency trend */}
        <div className="card">
          <h3 className="heading-3" style={{ marginBottom: 20 }}>Latency Trend</h3>
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={analytics.latency_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-1)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--text-3)" tick={{ fontSize: 11 }} />
                <YAxis stroke="var(--text-3)" tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={CHART_STYLE} />
                <Line
                  type="monotone"
                  dataKey="latency"
                  stroke="var(--accent)"
                  strokeWidth={1.5}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Modality distribution */}
        <div className="card">
          <h3 className="heading-3" style={{ marginBottom: 20 }}>Modality Distribution</h3>
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={analytics.modality_distribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-1)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--text-3)" tick={{ fontSize: 11 }} />
                <YAxis stroke="var(--text-3)" tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={CHART_STYLE} />
                <Bar dataKey="value" fill="var(--accent)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
