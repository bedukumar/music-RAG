import { useState, useEffect } from 'react';
import { SystemAPI, PipelineAPI } from '../api/client';
import { Activity, Server, Cpu, Music2 } from 'lucide-react';

export default function Dashboard() {
  const [metrics, setMetrics] = useState<any>(null);
  const [pipelineStats, setPipelineStats] = useState<any>(null);

  useEffect(() => {
    SystemAPI.metrics().then(setMetrics).catch(console.error);
    PipelineAPI.getStats().then(setPipelineStats).catch(console.error);
  }, []);

  const totalMedia      = pipelineStats?.total_media || 0;
  const pendingJobs     = pipelineStats?.jobs?.pending || 0;
  const processingJobs  = pipelineStats?.jobs?.processing || 0;
  const cpuUsage        = metrics?.cpu_usage_percent !== undefined
    ? metrics.cpu_usage_percent.toFixed(1)
    : '—';
  const memoryUsage     = metrics?.memory_usage_mb || '—';

  const stats = [
    {
      label: 'CPU Usage',
      value: `${cpuUsage}%`,
      meta: `${memoryUsage} MB memory`,
      icon: <Cpu size={14} color="var(--text-3)" />,
    },
    {
      label: 'Active Workers',
      value: '1',
      meta: <span className="badge badge-success">Online</span>,
      icon: <Server size={14} color="var(--text-3)" />,
    },
    {
      label: 'Jobs in Queue',
      value: pendingJobs + processingJobs,
      meta: `${processingJobs} processing`,
      icon: <Activity size={14} color="var(--text-3)" />,
    },
    {
      label: 'Total Media',
      value: totalMedia,
      meta: 'registered items',
      icon: <Music2 size={14} color="var(--text-3)" />,
    },
  ];

  return (
    <div className="animate-fade-in">
      {/* Page header */}
      <div className="page-header">
        <div>
          <h1 className="heading-1">Dashboard</h1>
          <p className="text-muted" style={{ marginTop: 4 }}>System overview and pipeline health</p>
        </div>
      </div>

      {/* Stat grid */}
      <div className="grid grid-cols-4 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="stat-card">
            <div className="stat-label">
              {s.label}
              {s.icon}
            </div>
            <div className="stat-value">{s.value}</div>
            <div className="stat-meta">{s.meta}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
