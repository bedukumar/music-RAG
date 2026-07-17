/**
 * Job List Component
 */

const JobList = {
    render() {
        return `
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                    <div style="display: flex; gap: 1rem; align-items: center;">
                        <select id="job-status-filter" class="form-control" style="width: auto; padding: 0.5rem 2rem 0.5rem 1rem;" onchange="JobList.loadData()">
                            <option value="">All Statuses</option>
                            <option value="pending">Pending</option>
                            <option value="processing">Processing</option>
                            <option value="completed">Completed</option>
                            <option value="failed">Failed</option>
                        </select>
                    </div>
                    <button class="btn btn-outline" onclick="JobList.loadData()">
                        Refresh
                    </button>
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Job ID</th>
                                <th>Media ID</th>
                                <th>Modality</th>
                                <th>Status</th>
                                <th>Created</th>
                                <th>Duration</th>
                                <th>Retries</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="job-table-body">
                            <tr><td colspan="8" style="text-align: center; padding: 2rem;">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
                
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
                    <div style="font-size: 0.85rem; color: var(--text-secondary);" id="job-pagination-info">Showing 0-0 of 0</div>
                    <div style="display: flex; gap: 0.5rem;">
                        <button class="btn btn-outline btn-icon" onclick="JobList.prevPage()" id="job-btn-prev" disabled>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"></polyline></svg>
                        </button>
                        <button class="btn btn-outline btn-icon" onclick="JobList.nextPage()" id="job-btn-next" disabled>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
                        </button>
                    </div>
                </div>
            </div>
        `;
    },

    offset: 0,
    limit: 15,
    total: 0,
    currentViewedJobId: null,

    async mount() {
        document.getElementById('page-title').textContent = 'Job Management';
        await this.loadData();
        this.wsHandler = this.handleWsEvent.bind(this);
        ws.on('event:all', this.wsHandler);
        this.startPolling();
    },

    unmount() {
        if (this.wsHandler) {
            ws.off('event:all', this.wsHandler);
        }
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    },

    handleWsEvent(event) {
        // Mark data as stale
        this.needsRefresh = true;
    },

    startPolling() {
        this.needsRefresh = false;
        this.refreshInterval = setInterval(() => {
            if (this.needsRefresh) {
                this.loadDataSilently();
                if (this.currentViewedJobId && document.getElementById('current-modal') && document.getElementById('current-modal').classList.contains('active')) {
                    this.viewDetails(this.currentViewedJobId, true);
                }
                this.needsRefresh = false;
            }
        }, 2000); // Check every 2 seconds (Production standard)
    },

    async loadDataSilently() {
        const tbody = document.getElementById('job-table-body');
        const statusFilter = document.getElementById('job-status-filter').value;
        try {
            const data = await api.getJobs(this.offset, this.limit, statusFilter);
            this.total = data.total;
            this.renderRows(data.items);
            this.updatePagination();
        } catch (e) {}
    },

    async loadData() {
        const tbody = document.getElementById('job-table-body');
        const statusFilter = document.getElementById('job-status-filter').value;
        
        try {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 2rem;"><div class="spinner" style="margin:0 auto;"></div></td></tr>';
            
            const data = await api.getJobs(this.offset, this.limit, statusFilter);
            this.total = data.total;
            
            this.renderRows(data.items);
            this.updatePagination();
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 2rem; color: var(--status-danger);">Failed to load jobs</td></tr>`;
        }
    },
    
    renderRows(items) {
        const tbody = document.getElementById('job-table-body');
        
        if (!items || items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-muted);">No jobs found.</td></tr>';
            return;
        }
        
        tbody.innerHTML = '';
        
        items.forEach(item => {
            const badgeClass = Utils.getStatusBadgeClass(item.status);
            
            let duration = '-';
            if (item.started_at && item.completed_at) {
                const s = new Date(item.started_at).getTime();
                const c = new Date(item.completed_at).getTime();
                duration = Utils.formatDuration(c - s);
            }
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-family: monospace; font-size: 0.8rem;">${item.id.substring(0,8)}...</td>
                <td>
                    <a href="javascript:void(0)" onclick="app.navigate('pipeline', '${item.media_id}')" style="color: #8b5cf6; text-decoration: none;">
                        ${item.media_id.substring(0,8)}...
                    </a>
                </td>
                <td style="text-transform: capitalize;">${item.modality}</td>
                <td><span class="badge ${badgeClass}">${item.status}</span></td>
                <td>${Utils.formatDate(item.created_at)}</td>
                <td>${duration}</td>
                <td>${item.retry_count}</td>
                <td>
                    <div style="display: flex; gap: 0.5rem;">
                        ${item.status === 'failed' ? `
                            <button class="btn btn-outline btn-icon" onclick="JobList.retryJob('${item.id}')" title="Retry Job">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
                            </button>
                        ` : ''}
                        ${(item.status === 'pending' || item.status === 'processing') ? `
                            <button class="btn btn-danger btn-icon" onclick="JobList.cancelJob('${item.id}')" title="Cancel Job">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="9" y1="9" x2="15" y2="15"></line><line x1="15" y1="9" x2="9" y2="15"></line></svg>
                            </button>
                        ` : ''}
                        <button class="btn btn-ghost btn-icon" onclick="JobList.viewDetails('${item.id}')" title="View Details">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    },
    
    updatePagination() {
        const info = document.getElementById('job-pagination-info');
        const prevBtn = document.getElementById('job-btn-prev');
        const nextBtn = document.getElementById('job-btn-next');
        
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
    
    async retryJob(id) {
        try {
            await api.retryJob(id);
            Utils.showToast('Success', 'Job queued for retry', 'success');
            this.loadData();
        } catch (e) {}
    },
    
    async cancelJob(id) {
        if (!confirm("Cancel this job?")) return;
        try {
            await api.cancelJob(id);
            Utils.showToast('Success', 'Job cancelled', 'info');
            this.loadData();
        } catch (e) {}
    },
    
    async viewDetails(id, isSilentUpdate = false) {
        this.currentViewedJobId = id;
        try {
            const details = await api.getJob(id);
            let pipelineHtml = '';
            
            try {
                const status = await api.getPipelineStatus(details.media_id);
                const pState = status.pipelines?.[details.modality];
                if (pState && pState.stages && pState.stages.length > 0) {
                    pipelineHtml = '<div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color);"><strong style="color:var(--text-secondary); display:block; margin-bottom: 0.5rem;">Pipeline Stages:</strong><ul style="list-style:none; padding:0; margin:0; font-size: 0.85rem;">';
                    const stageOrder = ['VALIDATION', 'NORMALIZATION', 'PREPROCESSING', 'CHUNKING', 'EMBEDDING', 'POST_PROCESSING', 'VECTOR_STORAGE'];
                    stageOrder.forEach(stage => {
                        const sr = pState.stages.find(s => s.stage === stage);
                        let icon = '<span style="display:inline-block; width:16px;">⏳</span>';
                        let color = 'var(--text-muted)';
                        let extra = '';
                        if (sr) {
                            if (sr.status === 'completed') { icon = '<span style="display:inline-block; width:16px;">✅</span>'; color = 'var(--status-success)'; }
                            else if (sr.status === 'running') { icon = '<span class="spinner" style="display:inline-block; width:14px; height:14px; border-width:2px; vertical-align:middle; border-top-color:var(--primary-color);"></span>'; color = 'var(--primary-color)'; extra = ' <em>(processing...)</em>'; }
                            else if (sr.status === 'failed') { icon = '<span style="display:inline-block; width:16px;">❌</span>'; color = 'var(--status-danger)'; }
                            
                            if (sr.error_message) {
                                extra += `<div style="margin-top: 0.25rem; font-size: 0.75rem; color: var(--status-danger); padding-left: 20px;">${Utils.escapeHtml(sr.error_message)}</div>`;
                            }
                        }
                        pipelineHtml += `<li style="margin-bottom: 0.5rem; color: ${color};">${icon} <span style="font-weight:500;">${stage.replace('_', ' ')}</span>${extra}</li>`;
                    });
                    pipelineHtml += '</ul></div>';
                }
            } catch(e) {
                console.log("Could not fetch pipeline status", e);
            }
            
            let html = `
                <div style="font-family: monospace; font-size: 0.85rem;">
                    <div style="margin-bottom: 0.5rem;"><strong style="color:var(--text-secondary)">Job ID:</strong> ${details.id}</div>
                    <div style="margin-bottom: 0.5rem;"><strong style="color:var(--text-secondary)">Media ID:</strong> ${details.media_id}</div>
                    <div style="margin-bottom: 0.5rem;"><strong style="color:var(--text-secondary)">Modality:</strong> ${details.modality}</div>
                    <div style="margin-bottom: 0.5rem;"><strong style="color:var(--text-secondary)">Status:</strong> <span class="badge ${Utils.getStatusBadgeClass(details.status)}">${details.status}</span></div>
                    <div style="margin-bottom: 0.5rem;"><strong style="color:var(--text-secondary)">Created:</strong> ${Utils.formatDate(details.created_at)}</div>
                    <div style="margin-bottom: 0.5rem;"><strong style="color:var(--text-secondary)">Started:</strong> ${Utils.formatDate(details.started_at)}</div>
                    <div style="margin-bottom: 0.5rem;"><strong style="color:var(--text-secondary)">Completed:</strong> ${Utils.formatDate(details.completed_at)}</div>
                    <div style="margin-bottom: 0.5rem;"><strong style="color:var(--text-secondary)">Retries:</strong> ${details.retry_count} / ${details.max_retries}</div>
                </div>
            `;
            
            if (details.error_message) {
                html += `
                    <div style="margin-top: 1rem; padding: 1rem; background: rgba(239, 68, 68, 0.1); border-left: 3px solid var(--status-danger); border-radius: 4px;">
                        <div style="color: var(--status-danger); font-weight: 600; font-size: 0.85rem; margin-bottom: 0.5rem;">Error Output</div>
                        <div style="font-family: monospace; white-space: pre-wrap; font-size: 0.8rem; word-break: break-all;">${Utils.escapeHtml(details.error_message)}</div>
                    </div>
                `;
            }
            
            html += pipelineHtml;
            
            if (isSilentUpdate && document.getElementById('modal-content')) {
                // If it's a silent update and modal is already showing this job, just update the content inside without flickering the backdrop
                document.getElementById('modal-title').textContent = 'Job Details';
                document.getElementById('modal-content').innerHTML = html;
            } else {
                Utils.showModal('Job Details', html, `<button class="btn btn-primary" onclick="Utils.closeModal()">Close</button>`);
                
                // Set up event listener to clear currentViewedJobId on modal close
                const modal = document.getElementById('modal');
                const overlay = modal.querySelector('.modal-overlay');
                const closeBtn = modal.querySelector('.modal-close');
                
                const clearJobId = () => { this.currentViewedJobId = null; };
                if (overlay) overlay.addEventListener('click', clearJobId, {once: true});
                if (closeBtn) closeBtn.addEventListener('click', clearJobId, {once: true});
                
                // Add listener to the 'Close' button inside modal actions too
                const closeActionBtn = document.querySelector('#modal-actions button.btn-primary');
                if (closeActionBtn) closeActionBtn.addEventListener('click', clearJobId, {once: true});
            }
        } catch(e) {
            console.error(e);
        }
    }
};
