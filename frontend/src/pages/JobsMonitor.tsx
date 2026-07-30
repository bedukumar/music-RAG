import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { JobsAPI } from '../api/client';
import { RefreshCw, XCircle, CheckCircle, Clock, X } from 'lucide-react';

type JobStatus = 'completed' | 'failed' | 'processing' | string;

function StatusBadge({ status }: { status: JobStatus }) {
  if (status === 'completed') return <span className="badge badge-success">Completed</span>;
  if (status === 'failed')    return <span className="badge badge-danger">Failed</span>;
  if (status === 'processing') return <span className="badge badge-info">Processing</span>;
  return <span className="badge">{status}</span>;
}

function StatusIcon({ status }: { status: JobStatus }) {
  const s = status.toLowerCase();
  if (s === 'completed') return <CheckCircle size={14} color="var(--success)" />;
  if (s === 'failed')    return <XCircle     size={14} color="var(--danger)" />;
  if (s === 'processing') return <RefreshCw  size={14} color="var(--info)" className="spin" />;
  return <Clock size={14} color="var(--text-3)" />;
}

export default function JobsMonitor() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [jobDetails, setJobDetails] = useState<any | null>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  const fetchJobs = () => {
    JobsAPI.list({ limit: 50 })
      .then(res => setJobs(res.items || []))
      .catch(console.error);
  };

  useEffect(() => { fetchJobs(); }, []);

  const handleViewDetails = async (id: string) => {
    setSelectedJobId(id);
    setIsLoadingDetails(true);
    try {
      const details = await JobsAPI.get(id);
      setJobDetails(details);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoadingDetails(false);
    }
  };

  const handleCloseModal = () => {
    setSelectedJobId(null);
    setJobDetails(null);
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="heading-1">Jobs Monitor</h1>
          <p className="text-muted" style={{ marginTop: 4 }}>Track background ingestion and pipeline tasks</p>
        </div>
        <button className="btn btn-secondary" onClick={fetchJobs}>
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      {/* Jobs table */}
      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Modality</th>
              <th>Media ID</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 && (
              <tr>
                <td colSpan={5}>
                  <div className="empty-state">No jobs found.</div>
                </td>
              </tr>
            )}
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>
                  <div className="flex items-center gap-2">
                    <StatusIcon status={job.status} />
                    <StatusBadge status={job.status} />
                  </div>
                </td>
                <td style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                  {job.modality}
                </td>
                <td style={{ color: 'var(--text-3)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                  {job.media_id}
                </td>
                <td style={{ color: 'var(--text-2)', fontSize: 12 }}>
                  {new Date(job.created_at).toLocaleString()}
                </td>
                <td>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: 12, height: 26, padding: '0 10px' }}
                    onClick={() => handleViewDetails(job.id)}
                  >
                    Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Job details modal */}
      {selectedJobId && createPortal(
        <div
          className="modal-overlay animate-fade-in"
          onClick={(e) => { if (e.target === e.currentTarget) handleCloseModal(); }}
        >
          <div className="modal" style={{ maxWidth: 560 }}>
            {/* Modal header */}
            <div className="modal-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <h2 className="heading-2">Job Details</h2>
                <p className="text-muted" style={{ marginTop: 2, fontSize: 12 }}>Pipeline execution stages</p>
              </div>
              <button className="btn-icon" onClick={handleCloseModal}>
                <X size={14} />
              </button>
            </div>

            {/* Modal body */}
            <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
              {isLoadingDetails ? (
                <div className="flex justify-center" style={{ padding: '40px 0' }}>
                  <RefreshCw size={20} className="spin" color="var(--text-3)" />
                </div>
              ) : jobDetails ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {/* Summary row */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr',
                      gap: 16,
                      padding: '14px 16px',
                      background: 'var(--bg-1)',
                      border: '1px solid var(--border-1)',
                      borderRadius: 'var(--r-2)',
                    }}
                  >
                    <div>
                      <p style={{ fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>Status</p>
                      <StatusBadge status={jobDetails.status} />
                    </div>
                    <div>
                      <p style={{ fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>Modality</p>
                      <span style={{ fontSize: 13, fontFamily: 'var(--font-mono)', color: 'var(--text-2)' }}>{jobDetails.modality}</span>
                    </div>
                  </div>

                  {/* Pipeline stages */}
                  <div>
                    <p style={{ fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>Pipeline Stages</p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      {jobDetails.pipeline_state?.stages?.map((stage: any, idx: number) => (
                        <div
                          key={idx}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '10px 12px',
                            background: 'var(--bg-1)',
                            borderRadius: 'var(--r-1)',
                          }}
                        >
                          <div className="flex items-center gap-2">
                            <StatusIcon status={stage.status} />
                            <span style={{ fontSize: 13, fontWeight: 500 }}>{stage.stage}</span>
                          </div>
                          <div className="flex items-center gap-3">
                            {stage.duration_ms !== undefined && (
                              <span style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                                {Math.round(stage.duration_ms)}ms
                              </span>
                            )}
                            <StatusBadge status={stage.status} />
                          </div>
                        </div>
                      )) || (
                        <div className="empty-state" style={{ padding: '24px 0', fontSize: 12 }}>
                          No pipeline stages recorded yet.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="empty-state" style={{ color: 'var(--danger)' }}>
                  Failed to load job details.
                </div>
              )}
            </div>

            {/* Modal footer */}
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={handleCloseModal}>Close</button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
