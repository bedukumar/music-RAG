import React, { useState, useEffect, useRef } from 'react';
import { UploadCloud, Play, Pause, RotateCcw, AlertTriangle, CheckCircle, Clock, Info, X } from 'lucide-react';
import { BulkUploadAPI } from '../api/client';
import BulkUploadErrorsModal from '../components/BulkUploadErrorsModal';

interface BulkUploadItem {
  id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'paused';
  total_rows: number;
  processed_rows: number;
  failed_rows: number;
  created_at: string;
}

export default function BulkUpload() {
  const [uploads, setUploads] = useState<BulkUploadItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const [selectedErrorId, setSelectedErrorId] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchUploads = async () => {
    try {
      const data = await BulkUploadAPI.list({ limit: 20 });
      setUploads(data.items || []);
    } catch (err) {
      console.error('Failed to fetch bulk uploads:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUploads();
    
    // Poll every 3 seconds if any upload is active
    const interval = setInterval(() => {
      setUploads(current => {
        const hasActive = current.some(u => ['pending', 'processing'].includes(u.status));
        if (hasActive) {
          fetchUploads();
        }
        return current;
      });
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const handleFile = async (file: File) => {
    setUploading(true);
    setUploadMessage(null);
    try {
      await BulkUploadAPI.create(file);
      await fetchUploads();
      setUploadMessage("Upload received. Your file has been queued for processing. You can leave this page — processing will continue in the background.");
      setTimeout(() => setUploadMessage(null), 8000);
    } catch (err) {
      console.error('Upload failed:', err);
      alert('Upload failed. See console for details.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handlePause = async (id: string) => {
    await BulkUploadAPI.pause(id);
    fetchUploads();
  };

  const handleResume = async (id: string) => {
    await BulkUploadAPI.resume(id);
    fetchUploads();
  };

  const handleRetry = async (id: string) => {
    await BulkUploadAPI.retry(id);
    fetchUploads();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle size={16} color="var(--success)" />;
      case 'failed': return <AlertTriangle size={16} color="var(--error)" />;
      case 'paused': return <Pause size={16} color="var(--warning)" />;
      case 'processing': return <Play size={16} color="var(--accent)" />;
      default: return <Clock size={16} color="var(--text-2)" />;
    }
  };

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 style={{ margin: 0 }}>Bulk Upload</h2>
            <button 
              onClick={() => setShowInfo(true)}
              style={{ background: 'none', border: 'none', color: 'var(--text-2)', cursor: 'pointer', display: 'flex', padding: '4px' }}
              title="How to use Bulk Upload"
            >
              <Info size={18} />
            </button>
          </div>
          <p className="page-subtitle" style={{ marginTop: '4px' }}>Upload CSV or Excel files to ingest media catalog items in batch.</p>
        </div>
      </div>

      <div 
        style={{
          border: `2px dashed ${isDragging ? 'var(--accent)' : 'var(--border)'}`,
          backgroundColor: isDragging ? 'rgba(var(--accent-rgb), 0.05)' : 'var(--bg-1)',
          borderRadius: '8px',
          padding: '40px',
          textAlign: 'center',
          marginBottom: '24px',
          transition: 'all 0.2s',
          cursor: 'pointer'
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <UploadCloud size={32} color={isDragging ? 'var(--accent)' : 'var(--text-2)'} style={{ margin: '0 auto 16px' }} />
        <h3 style={{ marginBottom: '8px', color: 'var(--text-1)' }}>Drag and drop your file here</h3>
        <p style={{ color: 'var(--text-2)', fontSize: '14px', marginBottom: '16px' }}>Supports .csv and .xlsx files</p>
        
        <input 
          type="file" 
          ref={fileInputRef}
          style={{ display: 'none' }}
          accept=".csv, .xlsx"
          onChange={handleFileChange}
        />
        <button 
          className="btn btn-primary" 
          disabled={uploading}
          onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
        >
          {uploading ? 'Uploading...' : 'Browse Files'}
        </button>
      </div>

      {uploadMessage && (
        <div style={{ padding: '16px', backgroundColor: 'rgba(var(--success-rgb), 0.1)', border: '1px solid var(--success)', borderRadius: '8px', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <CheckCircle size={20} color="var(--success)" />
          <div>
            <h4 style={{ margin: '0 0 4px', color: 'var(--text-1)' }}>Upload received</h4>
            <p style={{ margin: 0, color: 'var(--text-2)', fontSize: '13px' }}>{uploadMessage}</p>
          </div>
        </div>
      )}

      <div className="card">
        <h3 style={{ marginBottom: '16px' }}>Recent Uploads</h3>
        
        {loading ? (
          <p style={{ color: 'var(--text-2)' }}>Loading uploads...</p>
        ) : uploads.length === 0 ? (
          <p style={{ color: 'var(--text-2)' }}>No bulk uploads found. Start by uploading a CSV.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-2)', fontSize: '13px' }}>
                  <th style={{ padding: '12px 8px' }}>Filename</th>
                  <th style={{ padding: '12px 8px' }}>Status</th>
                  <th style={{ padding: '12px 8px' }}>Progress</th>
                  <th style={{ padding: '12px 8px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {uploads.map(upload => {
                  const progress = upload.total_rows > 0 
                    ? Math.round(((upload.processed_rows + upload.failed_rows) / upload.total_rows) * 100) 
                    : 0;
                  
                  return (
                    <tr key={upload.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '12px 8px', fontWeight: 500 }}>
                        {upload.filename}
                        <div style={{ fontSize: '12px', color: 'var(--text-2)', marginTop: '4px' }}>
                          {new Date(upload.created_at).toLocaleString()}
                        </div>
                      </td>
                      <td style={{ padding: '12px 8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', textTransform: 'capitalize' }}>
                          {getStatusIcon(upload.status)}
                          {upload.status}
                        </div>
                      </td>
                      <td style={{ padding: '12px 8px' }}>
                        <div style={{ width: '150px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px', color: 'var(--text-2)' }}>
                            <span>{progress}%</span>
                            <span>{upload.processed_rows + upload.failed_rows} / {upload.total_rows}</span>
                          </div>
                          <div style={{ height: '6px', backgroundColor: 'var(--bg-2)', borderRadius: '3px', overflow: 'hidden', display: 'flex' }}>
                            <div style={{ width: `${upload.total_rows > 0 ? (upload.processed_rows/upload.total_rows)*100 : 0}%`, backgroundColor: 'var(--success)', transition: 'width 0.3s' }} />
                            <div style={{ width: `${upload.total_rows > 0 ? (upload.failed_rows/upload.total_rows)*100 : 0}%`, backgroundColor: 'var(--error)', transition: 'width 0.3s' }} />
                          </div>
                          {upload.failed_rows > 0 && (
                            <div 
                              style={{ fontSize: '12px', color: 'var(--error)', marginTop: '4px', cursor: 'pointer', textDecoration: 'underline' }}
                              onClick={() => setSelectedErrorId(upload.id)}
                            >
                              {upload.failed_rows} errors
                            </div>
                          )}
                        </div>
                      </td>
                      <td style={{ padding: '12px 8px' }}>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          {['pending', 'processing'].includes(upload.status) && (
                            <button className="btn btn-secondary" onClick={() => handlePause(upload.id)} title="Pause" style={{ padding: '6px' }}>
                              <Pause size={14} />
                            </button>
                          )}
                          {upload.status === 'paused' && (
                            <button className="btn btn-secondary" onClick={() => handleResume(upload.id)} title="Resume" style={{ padding: '6px' }}>
                              <Play size={14} />
                            </button>
                          )}
                          {upload.status === 'failed' && (
                            <button className="btn btn-secondary" onClick={() => handleRetry(upload.id)} title="Retry" style={{ padding: '6px' }}>
                              <RotateCcw size={14} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedErrorId && (
        <BulkUploadErrorsModal 
          uploadId={selectedErrorId} 
          onClose={() => setSelectedErrorId(null)} 
        />
      )}

      {showInfo && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(2px)' }}>
          <div style={{ backgroundColor: 'var(--bg-2)', padding: '24px', borderRadius: '8px', maxWidth: '500px', width: '100%', border: '1px solid var(--border)', boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, color: 'var(--text-1)' }}>How to use Bulk Upload</h3>
              <button onClick={() => setShowInfo(false)} style={{ background: 'none', border: 'none', color: 'var(--text-2)', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
            <p style={{ color: 'var(--text-2)', fontSize: '14px', lineHeight: '1.6' }}>
              1. Download the sample CSV file to see the required format.<br/>
              2. Fill in your media data. <strong>title</strong>, <strong>media_type</strong>, and <strong>source_url</strong> (or <em>audio_path</em>) are required. You can optionally include a <strong>transcript_text</strong> column.<br/>
              3. Drag and drop your file into the upload zone above.<br/>
              4. Track progress in the table below. You can pause or retry jobs if needed.
            </p>
            <div style={{ marginTop: '24px', textAlign: 'right' }}>
              <a 
                href="/sample_bulk_upload.csv" 
                download
                className="btn btn-secondary" 
                style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
              >
                Download Sample CSV
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
