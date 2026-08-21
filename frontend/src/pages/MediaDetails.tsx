import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useParams, Link } from 'react-router-dom';
import { MediaAPI, PipelineAPI } from '../api/client';
import { Play, Upload, CheckCircle, Clock, X, RefreshCw, ArrowLeft, Edit, Copy, Volume2, FileText, Database, Cpu } from 'lucide-react';

export default function MediaDetails() {
  const { id } = useParams<{ id: string }>();
  const [media, setMedia] = useState<any>(null);
  const [pipelineStats, setPipelineStats] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);

  // Tabs
  const [activeTab, setActiveTab] = useState<'audio' | 'transcript' | 'metadata' | 'processing'>('audio');

  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeModality, setActiveModality] = useState<string | null>(null);
  const [isUpdateMode, setIsUpdateMode] = useState(false);
  
  // Form states
  const [textInput, setTextInput] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async (silent = false) => {
    if (!id) return;
    try {
      if (!silent) setLoading(true);
      const data = await MediaAPI.get(id);
      setMedia(data);
      const pipelineData = await PipelineAPI.getStatus(id);
      setPipelineStats(pipelineData);
    } catch (e) {
      console.error("Failed to load media details", e);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const hasModality = (mod: string) => media?.modality_statuses?.some((s: any) => s.modality === mod && s.data_available);
  const getModalityStatus = (mod: string) => media?.modality_statuses?.find((s: any) => s.modality === mod);

  const handleReprocess = async (modality?: string) => {
    if (!id) return;
    try {
      setIsProcessing(prev => ({ ...prev, [modality || 'all']: true }));
      if (modality) {
        await MediaAPI.reprocessModality(id, modality);
      } else {
        const validModalities = ['audio', 'transcript', 'metadata'].filter(hasModality);
        if (validModalities.length === 0) {
           alert("No data available to process.");
           return;
        }
        for (const mod of validModalities) {
            await MediaAPI.reprocessModality(id, mod);
        }
      }
      alert(`${modality || 'All available'} pipeline(s) re-triggered!`);
      const interval = setInterval(() => loadData(true), 2000);
      setTimeout(() => clearInterval(interval), 30000);
    } catch (e) {
      console.error(e);
      alert('Failed to start reprocessing.');
    } finally {
      setIsProcessing(prev => ({ ...prev, [modality || 'all']: false }));
    }
  };

  const handleOpenModal = (modality: string, isUpdate: boolean = false) => {
    setActiveModality(modality);
    setIsUpdateMode(isUpdate);
    setTextInput('');
    setSelectedFile(null);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setActiveModality(null);
    setTextInput('');
    setSelectedFile(null);
  };

  const submitModalData = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !activeModality) return;
    
    try {
      setIsUploading(true);
      setIsProcessing(prev => ({ ...prev, [`${activeModality}-upload`]: true }));
      
      if (activeModality === 'transcript') {
        if (!textInput.trim()) return alert('Transcript cannot be empty');
        if (textInput.length > 100000) return alert('Transcript is too long. Max 100,000 characters.');
        await MediaAPI.updateTranscript(id, textInput);
      } else if (activeModality === 'metadata') {
        if (!textInput.trim()) return alert('Metadata cannot be empty');
        if (textInput.length > 50000) return alert('Metadata is too large. Max 50,000 characters.');
        try {
          const parsed = JSON.parse(textInput);
          if (typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Metadata must be a JSON object');
          await MediaAPI.updateMetadata(id, parsed);
        } catch (err) {
          return alert('Invalid JSON format for metadata. It must be a valid JSON object.');
        }
      } else if (activeModality === 'audio') {
        if (!selectedFile) return alert('Please select an audio file');
        
        const getDuration = (file: File): Promise<number> => {
           return new Promise((resolve) => {
              const url = URL.createObjectURL(file);
              const audio = new Audio(url);
              audio.onloadedmetadata = () => { resolve(audio.duration); URL.revokeObjectURL(url); };
              audio.onerror = () => { resolve(0); URL.revokeObjectURL(url); };
           });
        };
        const duration = await getDuration(selectedFile);
        
        const uploadRes = await MediaAPI.upload(selectedFile);
        await MediaAPI.updateAudio(id, uploadRes.path, duration);
      }
      alert(`${activeModality} data updated successfully. You can now re-run the pipeline.`);
      await loadData(true);
      handleCloseModal();
    } catch (e) {
      console.error(e);
      alert(`Failed to update ${activeModality}.`);
    } finally {
      setIsProcessing(prev => ({ ...prev, [`${activeModality}-upload`]: false }));
      setIsUploading(false);
    }
  };

  const handleCopyTranscript = () => {
    if (media?.transcript_text) {
      navigator.clipboard.writeText(media.transcript_text);
      alert('Transcript copied to clipboard!');
    }
  };

  if (loading) {
    return <div className="flex justify-center p-8"><RefreshCw className="animate-pulse" size={32} /></div>;
  }

  if (!media) {
    return <div className="text-center p-8 text-danger">Media item not found.</div>;
  }

  // Calculate overall duration across all pipelines
  let totalDurationMs = 0;
  if (pipelineStats?.pipelines) {
     Object.values(pipelineStats.pipelines).forEach((p: any) => {
        p.stages?.forEach((s: any) => {
           if (s.duration_ms) totalDurationMs += s.duration_ms;
        });
     });
  }
  const totalDurationSeconds = (totalDurationMs / 1000).toFixed(2);

  const formatDuration = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const formatMs = (ms: number) => {
    if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
    return `${Math.round(ms)}ms`;
  };

  // Pipeline summary stats
  let totalStages = 0;
  let completedStages = 0;
  let failedStages = 0;
  if (pipelineStats?.pipelines) {
    Object.values(pipelineStats.pipelines).forEach((p: any) => {
      p.stages?.forEach((s: any) => {
        totalStages++;
        if (s.status === 'completed') completedStages++;
        if (s.status === 'failed') failedStages++;
      });
    });
  }

  return (
    <div className="md-page animate-fade-in">

      {/* ── HEADER ── */}
      <header className="md-header">
        <div className="md-header-back">
          <Link to="/media" className="btn-icon" aria-label="Back to media catalog">
            <ArrowLeft size={15} />
          </Link>
        </div>

        <div className="md-header-info">
          <h1 className="md-title">{media.title}</h1>
          <div className="md-subtitle">
            <span>{media.artist || 'Unknown Artist'}</span>
            {media.media_type && (
              <>
                <span className="md-dot">·</span>
                <span className="md-type-tag">{media.media_type}</span>
              </>
            )}
            {media.duration && (
              <>
                <span className="md-dot">·</span>
                <span>{formatDuration(media.duration)}</span>
              </>
            )}
          </div>
          <div className="md-id">{media.id}</div>
        </div>

        <div className="md-header-actions">
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => handleReprocess()}
            disabled={isProcessing['all']}
            aria-label="Reprocess all available modalities"
          >
            <RefreshCw size={13} className={isProcessing['all'] ? 'animate-pulse' : ''} />
            Reprocess All
          </button>
        </div>
      </header>

      {/* ── STATUS BADGES ── */}
      <div className="md-badges">
        {['audio', 'transcript', 'metadata'].map(mod => {
          const isAvail = hasModality(mod);
          return (
            <span
              key={mod}
              className={`md-badge badge badge-${isAvail ? 'success' : 'danger'}`}
              aria-label={`${mod} ${isAvail ? 'available' : 'missing'}`}
            >
              {mod.charAt(0).toUpperCase() + mod.slice(1)}: {isAvail ? 'Available' : 'Missing'}
            </span>
          );
        })}
      </div>

      {/* ── TABS ── */}
      <div className="tab-segmented-container">
        {[
          { id: 'audio',      label: 'Audio',               icon: <Volume2 size={14} />,  available: hasModality('audio')      },
          { id: 'transcript', label: 'Transcript',           icon: <FileText size={14} />, available: hasModality('transcript') },
          { id: 'metadata',   label: 'Metadata',             icon: <Database size={14} />, available: hasModality('metadata')   },
          { id: 'processing', label: 'Processing Pipeline',  icon: <Cpu size={14} />,      available: undefined                 },
        ].map(tab => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`tab-segmented-btn ${isActive ? 'active' : ''}`}
              aria-selected={isActive}
              role="tab"
            >
              <span className="tab-icon">{tab.icon}</span>
              <span>{tab.label}</span>
              {tab.available !== undefined && (
                <span
                  className={`tab-status-dot ${tab.available ? 'status-available' : 'status-missing'}`}
                  title={tab.available ? 'Data available' : 'Data missing'}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* ── TAB CONTENT ── */}
      <div key={activeTab} className="md-tab-content animate-fade-in" role="tabpanel">

        {/* ════ AUDIO TAB ════ */}
        {activeTab === 'audio' && (
          <div>
            <div className="md-section-header">
              <div>
                <h2 className="md-section-title">Audio Playback</h2>
              </div>
              <div className="md-section-actions">
                {hasModality('audio') && (
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleOpenModal('audio', true)}
                    aria-label="Replace audio file"
                  >
                    <Edit size={13} /> Replace
                  </button>
                )}
              </div>
            </div>

            {hasModality('audio') ? (
              <div className="md-audio-card">
                <div className="md-audio-meta">
                  <div className="md-audio-icon-wrap" aria-hidden="true">
                    <Volume2 size={20} />
                  </div>
                  <div className="md-audio-text">
                    <div className="md-audio-title">{media.title}</div>
                    <div className="md-audio-artist">{media.artist || 'Unknown Artist'}</div>
                  </div>
                  <span className="badge badge-success" style={{ fontSize: '10px' }}>Ready</span>
                </div>
                <div className="md-audio-player-wrap">
                  <audio
                    controls
                    src={MediaAPI.streamUrl(media.id)}
                    className="md-audio-player"
                    aria-label={`Play ${media.title}`}
                  >
                    Your browser does not support the audio element.
                  </audio>
                </div>
              </div>
            ) : (
              <div className="md-empty-state">
                <Volume2 size={36} className="md-empty-icon" aria-hidden="true" />
                <h3 className="md-empty-title">No audio file linked</h3>
                <p className="md-empty-body">
                  Upload an audio or video file to enable playback and pipeline processing for this media item.
                </p>
                <button className="btn btn-primary" onClick={() => handleOpenModal('audio', false)}>
                  <Upload size={13} /> Upload Audio
                </button>
              </div>
            )}
          </div>
        )}

        {/* ════ TRANSCRIPT TAB ════ */}
        {activeTab === 'transcript' && (
          <div>
            <div className="md-section-header">
              <div>
                <h2 className="md-section-title">Transcript</h2>
                {hasModality('transcript') && media.transcript_text && (
                  <p className="md-section-sub">
                    {media.transcript_text.split(/\s+/).filter((w: string) => w.length > 0).length} words
                  </p>
                )}
              </div>
              <div className="md-section-actions">
                {hasModality('transcript') && (
                  <>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={handleCopyTranscript}
                      aria-label="Copy transcript to clipboard"
                    >
                      <Copy size={13} /> Copy
                    </button>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleOpenModal('transcript', true)}
                      aria-label="Edit transcript"
                    >
                      <Edit size={13} /> Edit
                    </button>
                  </>
                )}
              </div>
            </div>

            {hasModality('transcript') && media.transcript_text ? (
              <div className="md-transcript-viewer">
                <p className="md-transcript-text">{media.transcript_text}</p>
              </div>
            ) : (
              <div className="md-empty-state">
                <FileText size={36} className="md-empty-icon" aria-hidden="true" />
                <h3 className="md-empty-title">No transcript available</h3>
                <p className="md-empty-body">
                  This media item does not have transcript data. Upload a transcript or lyrics to enable semantic search and embedding.
                </p>
                <button className="btn btn-primary" onClick={() => handleOpenModal('transcript', false)}>
                  <Upload size={13} /> Upload Transcript
                </button>
              </div>
            )}
          </div>
        )}

        {/* ════ METADATA TAB ════ */}
        {activeTab === 'metadata' && (
          <div>
            <div className="md-section-header">
              <div>
                <h2 className="md-section-title">Metadata</h2>
              </div>
              <div className="md-section-actions">
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleOpenModal('metadata', hasModality('metadata'))}
                  aria-label={hasModality('metadata') ? 'Edit metadata' : 'Upload metadata'}
                >
                  {hasModality('metadata') ? <><Edit size={13} /> Edit</> : <><Upload size={13} /> Upload</>}
                </button>
              </div>
            </div>

            <div className="md-meta-grid">
              {/* Basic info card */}
              <div className="md-meta-card">
                <div className="md-meta-card-title">Basic Information</div>
                {([
                  ['Title',          media.title],
                  ['Artist / Creator', media.artist],
                  ['Album / Show',   media.album || media.show_name],
                  ['Genre',          media.genre],
                  ['Language',       media.language],
                  ['Duration',       media.duration ? formatDuration(media.duration) : null],
                  ['Tags',           media.tags?.length ? media.tags.join(', ') : null],
                  ['Type',           media.media_type],
                ] as [string, string | null | undefined][]).map(([label, value]) => (
                  <div key={label} className="md-kv-row">
                    <span className="md-kv-label">{label}</span>
                    <span className="md-kv-value" title={value ?? ''}>
                      {value ?? <span className="md-kv-empty">—</span>}
                    </span>
                  </div>
                ))}
              </div>

              {/* Additional fields card */}
              <div className="md-meta-card">
                <div className="md-meta-card-title">Additional Fields</div>
                {media.metadata_fields && Object.keys(media.metadata_fields).length > 0 ? (
                  <pre className="md-code-block">
                    {JSON.stringify(media.metadata_fields, null, 2)}
                  </pre>
                ) : (
                  <div className="md-empty-inline">No additional metadata fields.</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ════ PROCESSING TAB ════ */}
        {activeTab === 'processing' && (
          <div>
            <div className="md-section-header">
              <div>
                <h2 className="md-section-title">Pipeline Processing</h2>
              </div>
              <div className="md-section-actions">
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => handleReprocess()}
                  disabled={isProcessing['all']}
                  aria-label="Reprocess all available modalities"
                >
                  <RefreshCw size={13} className={isProcessing['all'] ? 'animate-pulse' : ''} />
                  Reprocess All
                </button>
              </div>
            </div>

            {/* Summary stats */}
            <div className="md-pipeline-summary">
              <div className="md-pipeline-stat">
                <div className="md-pipeline-stat-label">Total Time</div>
                <div className="md-pipeline-stat-value">{totalDurationSeconds}s</div>
              </div>
              <div className="md-pipeline-stat">
                <div className="md-pipeline-stat-label">Stages</div>
                <div className="md-pipeline-stat-value">{totalStages}</div>
              </div>
              <div className="md-pipeline-stat">
                <div className="md-pipeline-stat-label">Completed</div>
                <div className={`md-pipeline-stat-value ${completedStages > 0 ? 'clr-success' : ''}`}>
                  {completedStages}
                </div>
              </div>
              <div className="md-pipeline-stat">
                <div className="md-pipeline-stat-label">Failed</div>
                <div className={`md-pipeline-stat-value ${failedStages > 0 ? 'clr-danger' : ''}`}>
                  {failedStages}
                </div>
              </div>
            </div>

            {/* Per-modality pipeline cards */}
            <div className="md-pipeline-modalities">
              {['audio', 'transcript', 'metadata'].map(mod => {
                const isAvailable = hasModality(mod);
                const statusInfo  = getModalityStatus(mod);
                const pState      = pipelineStats?.pipelines?.[mod];
                const isProc      = isProcessing[mod];
                const isUp        = isProcessing[`${mod}-upload`];
                const overallStatus = pState?.overall_status;

                return (
                  <div
                    key={mod}
                    className="md-pipeline-modality"
                    style={{ borderColor: !isAvailable ? 'rgba(239,68,68,0.2)' : undefined }}
                  >
                    {/* Modality header */}
                    <div className="md-pipeline-modality-header">
                      <div className="flex items-center gap-2" style={{ flexWrap: 'wrap', gap: '6px' }}>
                        <span className="md-pipeline-modality-name">{mod}</span>
                        <span className={`badge badge-${isAvailable ? 'success' : 'danger'}`}>
                          {isAvailable ? 'Available' : 'Missing'}
                        </span>
                        {statusInfo?.embedding_status && (
                          <span className={`badge badge-${
                            statusInfo.embedding_status === 'completed' ? 'success'
                            : statusInfo.embedding_status === 'failed'    ? 'danger'
                            : 'warning'
                          }`}>
                            Embedding: {statusInfo.embedding_status}
                          </span>
                        )}
                        {overallStatus && (
                          <span className={`badge badge-${
                            overallStatus === 'completed' ? 'success'
                            : overallStatus === 'failed'  ? 'danger'
                            : 'info'
                          }`}>
                            {overallStatus}
                          </span>
                        )}
                      </div>

                      <div className="flex gap-2">
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleReprocess(mod)}
                          disabled={isProc || !isAvailable}
                          aria-label={`Run ${mod} pipeline`}
                          title="Run Pipeline"
                        >
                          {isProc ? <RefreshCw size={13} className="animate-pulse" /> : <Play size={13} />}
                        </button>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleOpenModal(mod, isAvailable)}
                          disabled={isUp}
                          aria-label={isAvailable ? `Update ${mod} data` : `Upload ${mod} data`}
                          title={isAvailable ? 'Update Data' : 'Upload Data'}
                        >
                          {isAvailable ? <Edit size={13} /> : <Upload size={13} />}
                        </button>
                      </div>
                    </div>

                    {/* Timeline or empty state */}
                    {pState ? (
                      <div className="md-pipeline-timeline">
                        {pState.stages?.map((stage: any, idx: number) => {
                          const isLast = idx === pState.stages.length - 1;
                          return (
                            <div
                              key={idx}
                              className={`md-pipeline-stage md-stage-${stage.status}`}
                            >
                              <div className="md-stage-connector">
                                <div className="md-stage-dot" aria-hidden="true" />
                                {!isLast && <div className="md-stage-line" aria-hidden="true" />}
                              </div>
                              <div className="md-stage-body">
                                <span className="md-stage-name">{stage.stage?.replace(/_/g, ' ')}</span>
                                <div className="md-stage-right">
                                  {stage.duration_ms != null && (
                                    <span className="md-stage-duration">{formatMs(stage.duration_ms)}</span>
                                  )}
                                  <span className="md-stage-icon" aria-label={stage.status}>
                                    {stage.status === 'completed'  && <CheckCircle size={13} />}
                                    {stage.status === 'failed'     && <X           size={13} />}
                                    {stage.status === 'processing' && <RefreshCw   size={13} className="animate-pulse" />}
                                    {stage.status === 'pending'    && <Clock       size={13} />}
                                    {stage.status === 'skipped'    && <Clock       size={13} />}
                                  </span>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="md-empty-inline" style={{ margin: '12px 16px' }}>
                        No pipeline history for this modality.
                      </div>
                    )}

                    {/* Error banner */}
                    {statusInfo?.error_message && (
                      <div className="md-error-banner" role="alert">
                        {statusInfo.error_message}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

      </div>

      {/* ── UPLOAD / EDIT MODAL ── */}
      {isModalOpen && createPortal(
        <div className="modal-overlay animate-fade-in" role="dialog" aria-modal="true" aria-label={`${isUpdateMode ? 'Update' : 'Upload'} ${activeModality}`}>
          <div className="modal" style={{ padding: '24px' }}>
            <button
              onClick={handleCloseModal}
              className="btn-icon"
              aria-label="Close modal"
              style={{ position: 'absolute', top: '16px', right: '16px' }}
            >
              <X size={16} />
            </button>

            <h2 className="md-section-title" style={{ textTransform: 'capitalize', marginBottom: '4px' }}>
              {isUpdateMode ? 'Update' : 'Upload'} {activeModality}
            </h2>
            <p className="md-section-sub" style={{ marginBottom: '20px' }}>
              Provide the {isUpdateMode ? 'updated' : 'missing'} data to process.
            </p>

            <form onSubmit={submitModalData} className="flex flex-col gap-3">
              {activeModality === 'audio' && (
                <div className="input-group">
                  <label className="input-label" htmlFor="audio-upload">Audio / Video File</label>
                  <div style={{ background: 'var(--bg-2)', padding: '12px', borderRadius: 'var(--r-2)', border: '1px dashed var(--border-2)' }}>
                    <input
                      id="audio-upload"
                      required
                      type="file"
                      accept="audio/*,video/*"
                      className="text-small"
                      style={{ width: '100%', color: 'var(--text-1)' }}
                      onChange={e => setSelectedFile(e.target.files?.[0] || null)}
                    />
                  </div>
                </div>
              )}

              {activeModality === 'transcript' && (
                <div className="input-group">
                  <label className="input-label" htmlFor="transcript-input">Transcript Text / Lyrics</label>
                  <textarea
                    id="transcript-input"
                    required
                    className="input-field"
                    placeholder="Paste transcript here…"
                    style={{ minHeight: '160px' }}
                    value={textInput}
                    onChange={e => setTextInput(e.target.value)}
                  />
                </div>
              )}

              {activeModality === 'metadata' && (
                <div className="input-group">
                  <label className="input-label" htmlFor="metadata-input">Metadata (JSON)</label>
                  <textarea
                    id="metadata-input"
                    required
                    className="input-field"
                    placeholder='{"artist": "Queen", "year": 1975}'
                    style={{ minHeight: '160px', fontFamily: 'var(--font-mono)', fontSize: '12px' }}
                    value={textInput}
                    onChange={e => setTextInput(e.target.value)}
                  />
                </div>
              )}

              <div className="flex justify-end gap-3" style={{ marginTop: '8px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleCloseModal}
                  disabled={isUploading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isUploading}>
                  {isUploading ? (
                    <><RefreshCw size={13} className="animate-pulse" /> Uploading…</>
                  ) : (
                    'Save'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
