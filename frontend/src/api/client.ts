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

export const ChatAPI = {
  createConversation: (data: { title: string; system_prompt_version?: string; memory_window?: number }) => api.post('/chat/conversation', data).then(res => res.data),
  getConversation: (id: string) => api.get(`/chat/conversation/${id}`).then(res => res.data),
  getMessages: (id: string) => api.get(`/chat/conversation/${id}/messages`).then(res => res.data),
  deleteConversation: (id: string) => api.delete(`/chat/conversation/${id}`).then(res => res.data),
  truncateConversation: (conversationId: string, messageId: string) => api.delete(`/chat/conversation/${conversationId}/truncate/${messageId}`).then(res => res.data),
  chat: (data: any) => api.post('/chat', data).then(res => res.data),
  streamChat: async function* (data: any) {
    const response = await fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const reader = response.body?.getReader();
    const decoder = new TextDecoder('utf-8');
    
    if (!reader) return;
    
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';
      
      for (const chunk of lines) {
        const chunkLines = chunk.split('\n');
        for (const line of chunkLines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            try {
              yield JSON.parse(dataStr);
            } catch (e) {
              console.error('Error parsing SSE data', e, dataStr);
            }
          }
        }
      }
    }
  }
};

export const BulkUploadAPI = {
  create: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/bulk-uploads', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(res => res.data);
  },
  list: (params: { status?: string; offset?: number; limit?: number } = {}) => 
    api.get('/bulk-uploads', { params }).then(res => res.data),
  get: (id: string) => api.get(`/bulk-uploads/${id}`).then(res => res.data),
  errors: (id: string, params: { offset?: number; limit?: number } = {}) => 
    api.get(`/bulk-uploads/${id}/errors`, { params }).then(res => res.data),
  pause: (id: string) => api.post(`/bulk-uploads/${id}/pause`).then(res => res.data),
  resume: (id: string) => api.post(`/bulk-uploads/${id}/resume`).then(res => res.data),
  retry: (id: string) => api.post(`/bulk-uploads/${id}/retry`).then(res => res.data),
};

export default api;
