import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { MediaAPI } from '../api/client';
import { Play, Upload, Trash2, X, BarChart2 } from 'lucide-react';

export default function MediaCatalog() {
  const [media, setMedia] = useState<any[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [uploadForm, setUploadForm] = useState({ title: '', metadataJson: '', transcript: '' });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  useEffect(() => { loadMedia(); }, []);

  const loadMedia = () => {
    MediaAPI.list({ limit: 50 }).then(res => setMedia(res.items || [])).catch(console.error);
  };

  const handleDeleteMedia = async (id: string) => {
    if (!window.confirm('Delete this media item?')) return;
    try {
      await MediaAPI.delete(id);
      await loadMedia();
    } catch (e) {
      console.error(e);
      alert('Failed to delete. It may be locked by a processing job.');
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setUploadForm({ title: '', metadataJson: '', transcript: '' });
    setSelectedFile(null);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !uploadForm.title) return;
    try {
      setIsUploading(true);
      if (uploadForm.title.length > 500) { alert('Title too long (max 500 chars).'); return; }
      if (uploadForm.transcript && uploadForm.transcript.length > 100000) { alert('Transcript too long (max 100k chars).'); return; }

      let parsedMetadata = {};
      if (uploadForm.metadataJson) {
        if (uploadForm.metadataJson.length > 50000) { alert('Metadata too large (max 50k chars).'); return; }
        try {
          parsedMetadata = JSON.parse(uploadForm.metadataJson);
          if (typeof parsedMetadata !== 'object' || Array.isArray(parsedMetadata)) throw new Error();
        } catch {
          alert('Invalid JSON in Metadata field.');
          return;
        }
      }

      const getDuration = (file: File): Promise<number> =>
        new Promise(resolve => {
          const url = URL.createObjectURL(file);
          const audio = new Audio(url);
          audio.onloadedmetadata = () => { resolve(audio.duration); URL.revokeObjectURL(url); };
          audio.onerror = () => { resolve(0); URL.revokeObjectURL(url); };
        });

      const audioDuration = await getDuration(selectedFile);
      const uploadRes = await MediaAPI.upload(selectedFile);
      const createRes = await MediaAPI.create({
        media_type: 'song',
        title: uploadForm.title,
        transcript_text: uploadForm.transcript || undefined,
        metadata_fields: parsedMetadata,
        audio_path: uploadRes.path,
        duration: audioDuration > 0 ? audioDuration : undefined,
      });

      await MediaAPI.process(createRes.id, { modalities: ['audio', 'transcript', 'metadata'] });
      await loadMedia();
      handleCloseModal();
    } catch (error) {
      console.error('Upload failed', error);
      alert('Upload failed. Check the console for details.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="heading-1">Media Catalog</h1>
          <p className="text-muted" style={{ marginTop: 4 }}>Audio and video library — {media.length} items</p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <Upload size={13} />
          Upload Media
        </button>
      </div>

      {/* Upload modal */}
      {isModalOpen && createPortal(
        <div
          className="modal-overlay animate-fade-in"
          onClick={(e) => { if (e.target === e.currentTarget) handleCloseModal(); }}
        >
          <div className="modal" style={{ maxWidth: 480 }}>
            <div className="modal-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <h2 className="heading-2">Upload Media</h2>
                <p style={{ fontSize: 12, color: 'var(--text-2)', marginTop: 2 }}>Add a new track to your catalog</p>
              </div>
              <button className="btn-icon" onClick={handleCloseModal}>
                <X size={14} />
              </button>
            </div>

            <form onSubmit={handleFormSubmit}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div className="input-group">
                  <label className="input-label">Title <span style={{ color: 'var(--danger)' }}>*</span></label>
                  <input
                    required
                    type="text"
                    className="input-field"
                    placeholder="e.g. Bohemian Rhapsody"
                    value={uploadForm.title}
                    onChange={e => setUploadForm({ ...uploadForm, title: e.target.value })}
                  />
                </div>

                <div className="input-group">
                  <label className="input-label">Metadata (JSON)</label>
                  <textarea
                    className="input-field"
                    placeholder='{"artist": "Queen", "year": 1975, "genre": "Rock"}'
                    style={{ minHeight: 80, fontFamily: 'var(--font-mono)', fontSize: 12 }}
                    value={uploadForm.metadataJson}
                    onChange={e => setUploadForm({ ...uploadForm, metadataJson: e.target.value })}
                  />
                </div>

                <div className="input-group">
                  <label className="input-label">Transcript / Lyrics</label>
                  <textarea
                    className="input-field"
                    placeholder="Paste transcript here..."
                    style={{ minHeight: 88 }}
                    value={uploadForm.transcript}
                    onChange={e => setUploadForm({ ...uploadForm, transcript: e.target.value })}
                  />
                </div>

                <div className="input-group">
                  <label className="input-label">Audio File <span style={{ color: 'var(--danger)' }}>*</span></label>
                  <div
                    style={{
                      padding: '10px 12px',
                      background: 'var(--bg-1)',
                      border: '1px dashed var(--border-3)',
                      borderRadius: 'var(--r-2)',
                    }}
                  >
                    <input
                      required
                      type="file"
                      accept="audio/*,video/*"
                      style={{ fontSize: 12, color: 'var(--text-2)', width: '100%' }}
                      onChange={e => setSelectedFile(e.target.files?.[0] || null)}
                    />
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={handleCloseModal} disabled={isUploading}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isUploading}>
                  {isUploading ? 'Uploading...' : 'Upload & Process'}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* Media table */}
      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Type</th>
              <th>Duration</th>
              <th>Added</th>
              <th>Modalities</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {media.map((item) => {
              const hasModality = (mod: string) =>
                item.modality_statuses?.some((s: any) => s.modality === mod && s.data_available);
              return (
                <React.Fragment key={item.id}>
                  <tr>
                    <td>
                      <div className="flex items-center gap-3">
                        <button
                          className="btn-icon"
                          style={{ width: 26, height: 26, flexShrink: 0 }}
                          title="Play"
                        >
                          <Play size={11} />
                        </button>
                        <div>
                          <div style={{ fontWeight: 500, fontSize: 13 }}>{item.title}</div>
                          <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 1 }}>
                            {item.artist || 'Unknown Artist'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                        {item.media_type}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                      {item.duration ? `${Math.round(item.duration)}s` : '—'}
                    </td>
                    <td style={{ color: 'var(--text-2)', fontSize: 12 }}>
                      {new Date(item.created_at).toLocaleDateString()}
                    </td>
                    <td>
                      <div className="flex gap-1">
                        <span className={`badge badge-${hasModality('audio') ? 'success' : 'neutral'}`}>Audio</span>
                        <span className={`badge badge-${hasModality('transcript') ? 'success' : 'neutral'}`}>Transcript</span>
                        <span className={`badge badge-${hasModality('metadata') ? 'success' : 'neutral'}`}>Metadata</span>
                      </div>
                    </td>
                    <td>
                      <div className="flex gap-2">
                        <Link
                          to={`/media/${item.id}`}
                          className="btn btn-secondary"
                          style={{ height: 26, padding: '0 10px', fontSize: 12 }}
                        >
                          <BarChart2 size={11} />
                          Details
                        </Link>
                        <button
                          className="btn btn-danger"
                          style={{ height: 26, width: 26, padding: 0 }}
                          onClick={() => handleDeleteMedia(item.id)}
                          title="Delete"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                </React.Fragment>
              );
            })}
            {media.length === 0 && (
              <tr>
                <td colSpan={6}>
                  <div className="empty-state">No media found. Upload something to get started.</div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
