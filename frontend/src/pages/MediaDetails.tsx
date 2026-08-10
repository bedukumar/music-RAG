import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useParams, Link } from 'react-router-dom';
import { MediaAPI, PipelineAPI } from '../api/client';
import { Play, Upload, CheckCircle, Clock, X, RefreshCw, ArrowLeft, Edit, Copy, Info } from 'lucide-react';

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

  return (
    <div className="animate-fade-in pb-12">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link to="/media" className="btn-icon" style={{ background: 'var(--bg-tertiary)' }}>
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="heading-1" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {media.title}
          </h1>
          <div className="text-muted text-small mt-1 flex gap-3 items-center">
            <span>{media.artist || 'Unknown Artist'}</span>
            <span>•</span>
            <span style={{ textTransform: 'uppercase', letterSpacing: '1px', fontSize: '0.7rem' }}>{media.media_type}</span>
            {media.duration && (
              <>
                <span>•</span>
                <span>{Math.floor(media.duration / 60)}:{String(Math.floor(media.duration % 60)).padStart(2, '0')}</span>
              </>
            )}
            <span>•</span>
            <span style={{ fontFamily: 'monospace', opacity: 0.6 }}>ID: {media.id.substring(0, 8)}...</span>
          </div>
        </div>
      </div>

      <div className="flex gap-2 mb-8">
        {['audio', 'transcript', 'metadata'].map(mod => {
          const isAvail = hasModality(mod);
          return (
            <div key={mod} className={`badge badge-${isAvail ? 'success' : 'danger'}`} style={{ textTransform: 'capitalize', padding: '0.25rem 0.75rem', borderRadius: 'var(--radius-full)' }}>
              {mod}: {isAvail ? 'Available' : 'Missing'}
            </div>
          );
        })}
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b mb-6" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
        {['audio', 'transcript', 'metadata', 'processing'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab as any)}
            className={`px-4 py-3 text-small transition-colors ${activeTab === tab ? 'text-primary border-b-2 border-primary' : 'text-muted hover:text-primary'}`}
            style={{ fontWeight: activeTab === tab ? 600 : 400, textTransform: 'capitalize', borderBottomColor: activeTab === tab ? 'var(--accent)' : 'transparent', borderBottomStyle: 'solid', borderBottomWidth: '2px', marginBottom: '-1px' }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="glass-panel" style={{ padding: '2rem', minHeight: '400px' }}>
        
        {/* AUDIO TAB */}
        {activeTab === 'audio' && (
          <div className="flex flex-col gap-6">
            <h2 className="heading-2">Audio Playback</h2>
            {hasModality('audio') ? (
              <div className="flex flex-col gap-4">
                <audio 
                  controls 
                  src={MediaAPI.streamUrl(media.id)} 
                  style={{ width: '100%', outline: 'none', borderRadius: 'var(--radius-md)' }}
                >
                  Your browser does not support the audio element.
                </audio>
                <div className="text-small text-muted flex gap-2 items-center">
                  <Info size={14} />
                  <span>Audio file is successfully linked and available for playback.</span>
                </div>
              </div>
            ) : (
              <div className="text-center p-12 glass-card" style={{ background: 'rgba(0,0,0,0.2)', border: '1px dashed rgba(255,255,255,0.1)' }}>
                <p className="text-muted mb-4">No audio available for this media item.</p>
                <button className="btn btn-primary mx-auto" onClick={() => handleOpenModal('audio', false)}>
                   <Upload size={16}/> Upload Audio
                </button>
              </div>
            )}
          </div>
        )}

        {/* TRANSCRIPT TAB */}
        {activeTab === 'transcript' && (
          <div className="flex flex-col gap-6">
            <div className="flex justify-between items-center">
              <h2 className="heading-2" style={{ margin: 0 }}>Transcript</h2>
              {hasModality('transcript') && (
                <button className="btn btn-secondary btn-sm" onClick={handleCopyTranscript}>
                  <Copy size={14} /> Copy Text
                </button>
              )}
            </div>
            
            {hasModality('transcript') && media.transcript_text ? (
              <div className="glass-card" style={{ background: '#121216', padding: '1.5rem', maxHeight: '500px', overflowY: 'auto' }}>
                <p style={{ whiteSpace: 'pre-wrap', lineHeight: '1.8', color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
                  {media.transcript_text}
                </p>
                <div className="text-muted text-small mt-6 pt-4" style={{ borderTop: '1px solid rgba(255,255,255,0.1)', textAlign: 'right' }}>
                  Word count: {media.transcript_text.split(/\s+/).filter((w: string) => w.length > 0).length}
                </div>
              </div>
            ) : (
              <div className="text-center p-12 glass-card" style={{ background: 'rgba(0,0,0,0.2)', border: '1px dashed rgba(255,255,255,0.1)' }}>
                <p className="text-muted mb-4">No transcript available for this media item.</p>
                <button className="btn btn-primary mx-auto" onClick={() => handleOpenModal('transcript', false)}>
                   <Upload size={16}/> Add Transcript
                </button>
              </div>
            )}
          </div>
        )}

        {/* METADATA TAB */}
        {activeTab === 'metadata' && (
          <div className="flex flex-col gap-6">
            <h2 className="heading-2">Structured Metadata</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="flex flex-col gap-4">
                <div className="glass-card" style={{ background: '#121216', padding: '1.5rem' }}>
                  <h3 className="text-small mb-4 text-muted" style={{ textTransform: 'uppercase', letterSpacing: '1px' }}>Core Information</h3>
                  <table className="w-full text-small">
                    <tbody>
                      <tr className="border-b" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
                        <td className="py-2 text-muted">Title</td>
                        <td className="py-2 text-right">{media.title || '-'}</td>
                      </tr>
                      <tr className="border-b" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
                        <td className="py-2 text-muted">Artist / Creator</td>
                        <td className="py-2 text-right">{media.artist || '-'}</td>
                      </tr>
                      <tr className="border-b" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
                        <td className="py-2 text-muted">Album / Show</td>
                        <td className="py-2 text-right">{media.album || media.show_name || '-'}</td>
                      </tr>
                      <tr className="border-b" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
                        <td className="py-2 text-muted">Genre</td>
                        <td className="py-2 text-right">{media.genre || '-'}</td>
                      </tr>
                      <tr className="border-b" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
                        <td className="py-2 text-muted">Language</td>
                        <td className="py-2 text-right">{media.language || '-'}</td>
                      </tr>
                      <tr>
                        <td className="py-2 text-muted">Tags</td>
                        <td className="py-2 text-right">{media.tags?.length ? media.tags.join(', ') : '-'}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="flex flex-col gap-4">
                <div className="glass-card" style={{ background: '#121216', padding: '1.5rem' }}>
                  <h3 className="text-small mb-4 text-muted" style={{ textTransform: 'uppercase', letterSpacing: '1px' }}>Additional Fields (JSON)</h3>
                  {media.metadata_fields && Object.keys(media.metadata_fields).length > 0 ? (
                    <pre style={{ margin: 0, padding: '1rem', background: 'rgba(0,0,0,0.3)', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem', color: 'var(--text-secondary)', overflowX: 'auto' }}>
                      {JSON.stringify(media.metadata_fields, null, 2)}
                    </pre>
                  ) : (
                    <div className="text-muted text-small p-4 text-center" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-sm)' }}>
                      No additional metadata fields.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* PROCESSING TAB */}
        {activeTab === 'processing' && (
          <div className="flex flex-col gap-6">
             <div className="flex justify-between items-center mb-2">
                <div>
                   <h2 className="heading-2 mb-1" style={{ margin: 0 }}>Pipeline Processing</h2>
                   <p className="text-muted text-small">Total execution time across all stages: <strong style={{ color: 'var(--text-primary)' }}>{totalDurationSeconds}s</strong></p>
                </div>
                <button className="btn btn-primary" onClick={() => handleReprocess()} disabled={isProcessing['all']}>
                   {isProcessing['all'] ? <RefreshCw className="animate-pulse" size={16} /> : <RefreshCw size={16} />} 
                   Reprocess Available
                </button>
             </div>

             <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {['audio', 'transcript', 'metadata'].map(mod => {
                   const isAvailable = hasModality(mod);
                   const statusInfo = getModalityStatus(mod);
                   const pState = pipelineStats?.pipelines?.[mod];
                   const isProc = isProcessing[mod];
                   const isUp = isProcessing[`${mod}-upload`];
                   
                   return (
                     <div key={mod} className="glass-card flex flex-col gap-3" style={{ background: '#121216', padding: '1.5rem', border: `1px solid ${isAvailable ? 'rgba(255,255,255,0.1)' : 'rgba(239, 68, 68, 0.2)'}` }}>
                        <div className="flex justify-between items-center pb-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                           <div className="flex items-center gap-2">
                              <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>{mod}</div>
                              <span className={`badge badge-${isAvailable ? 'success' : 'danger'}`} style={{ fontSize: '0.65rem', padding: '0.1rem 0.4rem' }}>
                                 {isAvailable ? 'Available' : 'Missing'}
                              </span>
                           </div>
                           <div className="flex gap-2">
                              <button className="btn btn-secondary btn-sm" onClick={() => handleReprocess(mod)} disabled={isProc || !isAvailable} title="Run Pipeline">
                                {isProc ? <RefreshCw className="animate-pulse" size={14}/> : <Play size={14}/>}
                              </button>
                              <button className="btn btn-primary btn-sm" onClick={() => handleOpenModal(mod, isAvailable)} disabled={isUp} title={isAvailable ? "Update Data" : "Upload Data"}>
                                 {isAvailable ? <Edit size={14}/> : <Upload size={14}/>}
                              </button>
                           </div>
                        </div>

                        {statusInfo && statusInfo.embedding_status && (
                           <div className="text-small pt-1">
                             <div className="flex justify-between">
                                <span className="text-muted">Embedding:</span>
                                <span className={`badge badge-${statusInfo.embedding_status === 'completed' ? 'success' : statusInfo.embedding_status === 'failed' ? 'danger' : 'info'}`} style={{ fontSize: '0.65rem' }}>
                                   {statusInfo.embedding_status}
                                </span>
                             </div>
                             {statusInfo.error_message && (
                                <div className="text-danger mt-2 bg-red-900 bg-opacity-20 p-2 rounded text-xs break-words">
                                   Error: {statusInfo.error_message}
                                </div>
                             )}
                           </div>
                        )}
                        
                        {pState ? (
                           <div className="flex flex-col gap-3 mt-2">
                              <div className="flex justify-between text-small" style={{ background: 'rgba(255,255,255,0.03)', padding: '0.5rem', borderRadius: '4px' }}>
                                 <span className="text-muted">Status</span>
                                 <span className={`badge badge-${pState.overall_status === 'completed' ? 'success' : pState.overall_status === 'failed' ? 'danger' : 'info'}`}>
                                    {pState.overall_status}
                                 </span>
                              </div>
                              <div className="flex flex-col gap-2">
                                 {pState.stages?.map((stage: any, idx: number) => (
                                    <div key={idx} className="flex justify-between items-center text-small p-2 rounded" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.02)' }}>
                                       <span style={{ color: 'var(--text-secondary)' }}>{stage.stage}</span>
                                       <div className="flex items-center gap-2">
                                          {stage.duration_ms && <span className="text-muted" style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{Math.round(stage.duration_ms)}ms</span>}
                                          {stage.status === 'completed' ? <CheckCircle size={14} style={{ color: 'var(--success)' }} /> : stage.status === 'failed' ? <X size={14} style={{ color: 'var(--danger)' }} /> : stage.status === 'processing' ? <RefreshCw size={14} className="animate-pulse" style={{ color: 'var(--info)' }} /> : <Clock size={14} style={{ color: 'var(--warning)' }} />}
                                       </div>
                                    </div>
                                 ))}
                              </div>
                           </div>
                        ) : (
                           <div className="text-small text-muted p-6 text-center mt-2" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '4px', border: '1px dashed rgba(255,255,255,0.1)' }}>
                              No pipeline history.
                           </div>
                        )}
                     </div>
                   );
                })}
             </div>
          </div>
        )}

      </div>
      
      {isModalOpen && createPortal(
        <div className="modal-overlay animate-fade-in" style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.8)', display: 'flex', justifyContent: 'center', alignItems: 'flex-start', overflowY: 'auto', padding: '4rem 1rem', zIndex: 9999 }}>
          <div className="glass-card" style={{ width: '100%', maxWidth: '480px', position: 'relative', margin: 'auto', background: '#121216', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)' }}>
            <button 
              onClick={handleCloseModal} 
              className="btn-icon" 
              style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'transparent', border: 'none', cursor: 'pointer' }}
            >
              <X size={20} className="text-secondary" />
            </button>
            <h2 className="heading-2" style={{ textTransform: 'capitalize' }}>
               {isUpdateMode ? 'Update' : 'Upload'} {activeModality}
            </h2>
            <p className="text-muted" style={{ marginBottom: '1.5rem' }}>
               Provide the {isUpdateMode ? 'new' : 'missing'} data to process.
            </p>

            <form onSubmit={submitModalData} className="flex flex-col gap-3">
              {activeModality === 'audio' && (
                <div className="input-group">
                  <label className="input-label">Audio/Video File</label>
                  <div className="flex items-center gap-3" style={{ background: '#1a1a24', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px dashed rgba(255,255,255,0.2)' }}>
                    <input required type="file" accept="audio/*,video/*" className="text-small" style={{ width: '100%', color: 'var(--text-primary)' }} onChange={e => setSelectedFile(e.target.files?.[0] || null)} />
                  </div>
                </div>
              )}
              
              {activeModality === 'transcript' && (
                <div className="input-group">
                  <label className="input-label">Transcript Text / Lyrics</label>
                  <textarea required className="input-field" placeholder="Paste transcript here..." style={{ minHeight: '150px', background: '#1a1a24' }} value={textInput} onChange={e => setTextInput(e.target.value)} />
                </div>
              )}

              {activeModality === 'metadata' && (
                <div className="input-group">
                  <label className="input-label">Metadata (JSON format)</label>
                  <textarea required className="input-field" placeholder='{"artist": "Queen", "year": 1975}' style={{ minHeight: '150px', fontFamily: 'monospace', fontSize: '0.85rem', background: '#1a1a24' }} value={textInput} onChange={e => setTextInput(e.target.value)} />
                </div>
              )}
              
              <div className="flex justify-end gap-3" style={{ marginTop: '1rem' }}>
                <button type="button" className="btn btn-secondary" style={{ background: 'transparent' }} onClick={handleCloseModal} disabled={isUploading}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={isUploading}>
                  {isUploading ? 'Uploading...' : 'Save Data'}
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
