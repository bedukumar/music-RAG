import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useParams, Link } from 'react-router-dom';
import { MediaAPI, PipelineAPI } from '../api/client';
import { Play, Upload, CheckCircle, Clock, X, RefreshCw, ArrowLeft, Edit } from 'lucide-react';

export default function MediaDetails() {
  const { id } = useParams<{ id: string }>();
  const [media, setMedia] = useState<any>(null);
  const [pipelineStats, setPipelineStats] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);

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

  const handleReprocess = async (modality?: string) => {
    if (!id) return;
    try {
      setIsProcessing(prev => ({ ...prev, [modality || 'all']: true }));
      if (modality) {
        await MediaAPI.reprocessModality(id, modality);
      } else {
        // Build list of valid modalities so we don't send missing ones
        const validModalities = ['audio', 'transcript', 'metadata'].filter(hasModality);
        if (validModalities.length === 0) {
           alert("No data available to process.");
           return;
        }
        
        // Use reprocessModality to ensure locks are cleared and old state is cleaned up
        for (const mod of validModalities) {
            await MediaAPI.reprocessModality(id, mod);
        }
      }
      alert(`${modality || 'All available'} pipeline(s) re-triggered!`);
      // Start polling silently
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
        
        // Extract duration
        const getDuration = (file: File): Promise<number> => {
           return new Promise((resolve) => {
              const url = URL.createObjectURL(file);
              const audio = new Audio(url);
              audio.onloadedmetadata = () => { resolve(audio.duration); URL.revokeObjectURL(url); };
              audio.onerror = () => { resolve(0); URL.revokeObjectURL(url); };
           });
        };
        const duration = await getDuration(selectedFile);
        
        // Upload file
        const uploadRes = await MediaAPI.upload(selectedFile);
        
        // Save to DB
        // The API signature for updateAudio expects (media_id, audio_path, duration)
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
    <div className="animate-fade-in">
      <div className="flex items-center gap-4" style={{ marginBottom: '2rem' }}>
        <Link to="/media" className="btn-icon" style={{ background: 'var(--bg-tertiary)' }}>
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="heading-1" style={{ margin: 0 }}>{media.title}</h1>
          <p className="text-muted text-small">{media.artist || 'Unknown Artist'} • {media.media_type.toUpperCase()}</p>
        </div>
      </div>

      <div className="glass-panel" style={{ padding: '2rem', marginBottom: '2rem' }}>
         <div className="flex justify-between items-center mb-6">
            <div>
               <h2 className="heading-2">Pipeline Execution</h2>
               <p className="text-muted">Total execution time across all stages: <strong style={{ color: 'var(--text-primary)' }}>{totalDurationSeconds}s</strong></p>
            </div>
            <button className="btn btn-primary" onClick={() => handleReprocess()} disabled={isProcessing['all']}>
               {isProcessing['all'] ? <RefreshCw className="animate-pulse" size={16} /> : <RefreshCw size={16} />} 
               Reprocess Available
            </button>
         </div>

         <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {['audio', 'transcript', 'metadata'].map(mod => {
               const isAvailable = hasModality(mod);
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
