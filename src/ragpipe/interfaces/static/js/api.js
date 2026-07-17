/**
 * API Client
 */

class ApiClient {
    constructor(baseUrl = '/api/v1') {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const config = { ...defaultOptions, ...options };
        if (config.body instanceof FormData) {
            delete config.headers['Content-Type'];
        } else if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                let errorMsg = `HTTP Error ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.detail || errorMsg;
                } catch (e) {}
                
                throw new Error(errorMsg);
            }
            
            // Check if response is empty
            const text = await response.text();
            return text ? JSON.parse(text) : {};
            
        } catch (error) {
            console.error(`API Error on ${endpoint}:`, error);
            Utils.showToast('Error', error.message, 'error');
            throw error;
        }
    }

    // Media
    getMediaList(offset = 0, limit = 50, type = null) {
        let url = `/media?offset=${offset}&limit=${limit}`;
        if (type) url += `&media_type=${type}`;
        return this.request(url);
    }
    
    getMedia(id) {
        return this.request(`/media/${id}`);
    }
    
    createMedia(data) {
        return this.request('/media', { method: 'POST', body: data });
    }
    
    deleteMedia(id) {
        return this.request(`/media/${id}`, { method: 'DELETE' });
    }
    
    processMedia(id, modalities = null) {
        const body = modalities ? { modalities } : {};
        return this.request(`/media/${id}/process`, { method: 'POST', body });
    }
    
    reprocessModality(id, modality) {
        return this.request(`/media/${id}/reprocess/${modality}`, { method: 'POST' });
    }

    uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.request('/media/upload', {
            method: 'POST',
            body: formData
        });
    }

    // Jobs & Pipeline
    getSystemStats() {
        return this.request('/pipeline/stats');
    }
    
    getPipelineStatus(mediaId) {
        return this.request(`/pipeline/status/${mediaId}`);
    }
    
    getJobs(offset = 0, limit = 50, status = null) {
        let url = `/jobs?offset=${offset}&limit=${limit}`;
        if (status) url += `&status=${status}`;
        return this.request(url);
    }
    
    getJob(jobId) {
        return this.request(`/jobs/${jobId}`);
    }
    
    retryJob(jobId) {
        return this.request(`/jobs/${jobId}/retry`, { method: 'POST' });
    }
    
    cancelJob(jobId) {
        return this.request(`/jobs/${jobId}/cancel`, { method: 'POST' });
    }

    // Migrations
    getVersions(modality = null) {
        let url = '/embedding-versions';
        if (modality) url += `?modality=${modality}`;
        return this.request(url);
    }
    
    createVersion(data) {
        return this.request('/embedding-versions', { method: 'POST', body: data });
    }
    
    activateVersion(id) {
        return this.request(`/embedding-versions/${id}/activate`, { method: 'POST' });
    }
    
    getMigrations() {
        return this.request('/migrations');
    }
    
    startMigration(modality, toVersionId) {
        return this.request('/migrations', { 
            method: 'POST', 
            body: { modality, to_version_id: toVersionId } 
        });
    }
    
    switchIndex(migrationId) {
        return this.request(`/migrations/${migrationId}/switch`, { method: 'POST' });
    }
}

const api = new ApiClient();
