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

    async mount() {
        document.getElementById('page-title').textContent = 'Job Management';
        await this.loadData();
    },

    unmount() {},

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
    
    async viewDetails(id) {
        try {
            const details = await api.getJob(id);
            
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
            
            Utils.showModal('Job Details', html, `<button class="btn btn-primary" onclick="Utils.closeModal()">Close</button>`);
        } catch(e) {}
    }
};
