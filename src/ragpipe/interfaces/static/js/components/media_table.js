/**
 * Media Table Component
 */

const MediaTable = {
    render() {
        return `
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                    <div style="display: flex; gap: 1rem; align-items: center;">
                        <select id="media-type-filter" class="form-control" style="width: auto; padding: 0.5rem 2rem 0.5rem 1rem;" onchange="MediaTable.loadData()">
                            <option value="">All Types</option>
                            <option value="song">Song</option>
                            <option value="podcast">Podcast</option>
                            <option value="video">Video</option>
                        </select>
                    </div>
                    <button class="btn btn-primary" onclick="MediaTable.showCreateModal()">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                        Add Media
                    </button>
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Title</th>
                                <th>Audio Status</th>
                                <th>Transcript Status</th>
                                <th>Metadata Status</th>
                                <th>Added</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="media-table-body">
                            <tr><td colspan="7" style="text-align: center; padding: 2rem;">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
                
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
                    <div style="font-size: 0.85rem; color: var(--text-secondary);" id="media-pagination-info">Showing 0-0 of 0</div>
                    <div style="display: flex; gap: 0.5rem;">
                        <button class="btn btn-outline btn-icon" onclick="MediaTable.prevPage()" id="media-btn-prev" disabled>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"></polyline></svg>
                        </button>
                        <button class="btn btn-outline btn-icon" onclick="MediaTable.nextPage()" id="media-btn-next" disabled>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
                        </button>
                    </div>
                </div>
            </div>
        `;
    },

    offset: 0,
    limit: 10,
    total: 0,

    async mount() {
        document.getElementById('page-title').textContent = 'Media Library';
        await this.loadData();
    },

    unmount() {
        // cleanup
    },

    async loadData() {
        const tbody = document.getElementById('media-table-body');
        const typeFilter = document.getElementById('media-type-filter').value;
        
        try {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2rem;"><div class="spinner" style="margin:0 auto;"></div></td></tr>';
            
            const data = await api.getMediaList(this.offset, this.limit, typeFilter);
            this.total = data.total;
            
            this.renderRows(data.items);
            this.updatePagination();
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem; color: var(--status-danger);">Failed to load media</td></tr>`;
        }
    },
    
    renderRows(items) {
        const tbody = document.getElementById('media-table-body');
        
        if (!items || items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2rem; color: var(--text-muted);">No media found. Add some to get started.</td></tr>';
            return;
        }
        
        tbody.innerHTML = '';
        
        items.forEach(item => {
            // Helper to get status dot HTML
            const getStatusHtml = (modality) => {
                const status = item.modality_statuses?.find(s => s.modality === modality);
                if (!status) return `<span class="badge badge-skipped">N/A</span>`;
                
                const badgeClass = Utils.getStatusBadgeClass(status.embedding_status);
                let text = status.embedding_status;
                if (!status.data_available) text = "No Data";
                
                return `<span class="badge ${badgeClass}">${text}</span>`;
            };
            
            let typeIcon = '🎵';
            if (item.media_type === 'podcast') typeIcon = '🎙️';
            if (item.media_type === 'video') typeIcon = '🎬';
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span style="font-size: 1.2rem; margin-right: 0.5rem;">${typeIcon}</span> <span style="text-transform: capitalize;">${item.media_type}</span></td>
                <td>
                    <div style="font-weight: 500;">${Utils.escapeHtml(item.title)}</div>
                    ${item.artist ? `<div style="font-size: 0.75rem; color: var(--text-secondary);">${Utils.escapeHtml(item.artist)}</div>` : ''}
                </td>
                <td>${getStatusHtml('audio')}</td>
                <td>${getStatusHtml('transcript')}</td>
                <td>${getStatusHtml('metadata')}</td>
                <td>${Utils.formatDate(item.created_at)}</td>
                <td>
                    <div style="display: flex; gap: 0.5rem;">
                        <button class="btn btn-outline btn-icon" onclick="app.navigate('pipeline', '${item.id}')" title="View Pipeline">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                        </button>
                        <button class="btn btn-primary btn-icon" onclick="MediaTable.processMedia('${item.id}')" title="Process All Pending">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                        </button>
                        <button class="btn btn-danger btn-icon" onclick="MediaTable.deleteMedia('${item.id}')" title="Delete">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    },
    
    updatePagination() {
        const info = document.getElementById('media-pagination-info');
        const prevBtn = document.getElementById('media-btn-prev');
        const nextBtn = document.getElementById('media-btn-next');
        
        if (info) {
            const end = Math.min(this.offset + this.limit, this.total);
            info.textContent = `Showing ${this.total === 0 ? 0 : this.offset + 1}-${end} of ${this.total}`;
        }
        
        if (prevBtn) prevBtn.disabled = this.offset === 0;
        if (nextBtn) nextBtn.disabled = this.offset + this.limit >= this.total;
    },
    
    prevPage() {
        if (this.offset >= this.limit) {
            this.offset -= this.limit;
            this.loadData();
        }
    },
    
    nextPage() {
        if (this.offset + this.limit < this.total) {
            this.offset += this.limit;
            this.loadData();
        }
    },
    
    async processMedia(id) {
        try {
            const res = await api.processMedia(id);
            Utils.showToast('Success', `Triggered ${res.jobs_created} processing jobs.`, 'success');
            // Navigate to pipeline view to see it run
            app.navigate('pipeline', id);
        } catch (e) {
            // handled by api
        }
    },
    
    async deleteMedia(id) {
        if (!confirm("Are you sure you want to delete this media?")) return;
        try {
            await api.deleteMedia(id);
            Utils.showToast('Deleted', 'Media item removed.', 'success');
            this.loadData();
        } catch (e) {
            // Handled
        }
    },
    
    showCreateModal() {
        const html = `
            <form id="create-media-form" onsubmit="event.preventDefault(); MediaTable.submitCreate();">
                <div class="form-group">
                    <label class="form-label">Type</label>
                    <select id="create-type" class="form-control" required onchange="MediaTable.toggleFields()">
                        <option value="song">Song</option>
                        <option value="podcast">Podcast</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Title</label>
                    <input type="text" id="create-title" class="form-control" required placeholder="Track or Episode title">
                </div>
                <div class="form-group">
                    <label class="form-label">Artist / Creator</label>
                    <input type="text" id="create-artist" class="form-control" placeholder="Artist name">
                </div>
                <div class="form-group">
                    <label class="form-label">Custom Metadata (JSON)</label>
                    <textarea id="create-metadata" class="form-control" rows="3" placeholder='{"genre": "Rock", "year": 2023}'></textarea>
                </div>
                
                <div style="border-top: 1px solid var(--border-color); margin: 1rem 0; padding-top: 1rem;">
                    <h4 style="margin-bottom: 1rem; color: var(--text-secondary); font-size: 0.9rem;">Simulate Data Paths (For testing pipeline)</h4>
                    <div class="form-group">
                        <label class="form-label">Audio File</label>
                        <input type="file" id="create-audio-file" class="form-control" accept="audio/*">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Transcript / Lyrics Text</label>
                        <textarea id="create-text" class="form-control" rows="3" placeholder="Paste some text here..."></textarea>
                    </div>
                </div>
            </form>
        `;
        
        const footer = `
            <button class="btn btn-ghost" onclick="Utils.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="document.getElementById('create-media-form').dispatchEvent(new Event('submit'))">Create Item</button>
        `;
        
        Utils.showModal('Add Media', html, footer);
    },
    
    toggleFields() {
        // In a full implementation, this would show/hide specific fields based on type
    },
    
    async submitCreate() {
        const type = document.getElementById('create-type').value;
        const title = document.getElementById('create-title').value;
        const artist = document.getElementById('create-artist').value;
        const audioFile = document.getElementById('create-audio-file').files[0];
        const text = document.getElementById('create-text').value;
        const metadataStr = document.getElementById('create-metadata').value;
        
        let metadataFields = { source: "manual_entry" };
        if (metadataStr.trim()) {
            try {
                const parsed = JSON.parse(metadataStr);
                metadataFields = { ...metadataFields, ...parsed };
            } catch (e) {
                Utils.showToast('Error', 'Invalid JSON in metadata field', 'error');
                return;
            }
        }
        
        // Show loading state on button
        const submitBtn = document.querySelector('.modal-footer .btn-primary');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Uploading...';
        submitBtn.disabled = true;

        let audio = undefined;
        try {
            if (audioFile) {
                const res = await api.uploadFile(audioFile);
                audio = res.path;
            }
        } catch (e) {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
            return;
        }

        const data = {
            media_type: type,
            title: title,
            artist: artist || undefined,
            audio_path: audio,
            transcript_text: text || undefined,
            metadata_fields: metadataFields
        };
        
        try {
            const media = await api.createMedia(data);
            
            // Auto-trigger processing
            try {
                await api.processMedia(media.id);
            } catch (processError) {
                console.error("Auto-process failed:", processError);
                // Non-fatal, just continue
            }
            
            Utils.closeModal();
            Utils.showToast('Success', 'Media uploaded and processing started', 'success');
            this.loadData();
        } catch (e) {
            // Handled
        }
    }
};
