import axios from 'axios';

// Vite proxy handles /api/v1
const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const MediaAPI = {
  list: (params: { offset?: number; limit?: number; media_type?: string } = {}) => api.get('/media', { params }).then(res => res.data),
  get: (id: string) => api.get(`/media/${id}`).then(res => res.data),
  create: (data: any) => api.post('/media', data).then(res => res.data),
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/media/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(res => res.data);
  },
  process: (id: string, config: any = {}) => api.post(`/media/${id}/process`, config).then(res => res.data),
  reprocessModality: (id: string, modality: string) => api.post(`/media/${id}/reprocess/${modality}`).then(res => res.data),
  delete: (id: string) => api.delete(`/media/${id}`).then(res => res.data),
  updateTranscript: (id: string, transcript: string) => api.post(`/media/${id}/transcript`, null, { params: { transcript } }).then(res => res.data),
  updateMetadata: (id: string, metadata: any) => api.put(`/media/${id}/metadata`, metadata).then(res => res.data),
  updateAudio: (id: string, audio_path: string, duration?: number) => api.post(`/media/${id}/audio`, null, { params: { audio_path, duration } }).then(res => res.data),
};

export const JobsAPI = {
  list: (params: { status?: string; offset?: number; limit?: number } = {}) => api.get('/jobs', { params }).then(res => res.data),
  get: (id: string) => api.get(`/jobs/${id}`).then(res => res.data),
  retry: (id: string) => api.post(`/jobs/${id}/retry`).then(res => res.data),
  cancel: (id: string) => api.post(`/jobs/${id}/cancel`).then(res => res.data),
};

export const SystemAPI = {
  metrics: () => api.get('/system/metrics').then(res => res.data),
  events: (limit: number = 100) => api.get('/system/events', { params: { limit } }).then(res => res.data),
  workers: () => api.get('/workers').then(res => res.data),
};

export const CollectionsAPI = {
  list: () => api.get('/collections').then(res => res.data),
  health: (name: string) => api.get(`/collections/${name}/health`).then(res => res.data),
  optimize: (name: string) => api.post(`/collections/${name}/optimize`).then(res => res.data),
  delete: (name: string, force: boolean = true) => api.delete(`/collections/${name}`, { params: { force } }).then(res => res.data),
};

export const PipelineAPI = {
  getStatus: (mediaId: string) => api.get(`/pipeline/status/${mediaId}`).then(res => res.data),
  getStats: () => api.get('/pipeline/stats').then(res => res.data),
};

export default api;
