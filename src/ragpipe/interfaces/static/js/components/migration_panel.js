/**
 * Migration Panel Component
 */

const MigrationPanel = {
    render() {
        return `
            <div class="dashboard-grid">
                <div class="card" style="grid-column: span 1;">
                    <h3 style="margin-bottom: 1.5rem; color: var(--text-secondary);">Active Versions</h3>
                    <div id="active-versions-container">
                        Loading...
                    </div>
                    
                    <button class="btn btn-outline" style="width: 100%; margin-top: 1.5rem;" onclick="MigrationPanel.showCreateVersionModal()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                        Define New Version
                    </button>
                </div>
                
                <div class="card" style="grid-column: span 2;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                        <h3 style="color: var(--text-secondary);">Migration History</h3>
                        <button class="btn btn-ghost btn-icon" onclick="MigrationPanel.loadMigrations()" title="Refresh">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
                        </button>
                    </div>
                    
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Modality</th>
                                    <th>From -> To Version</th>
                                    <th>Status</th>
                                    <th>Progress</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="migration-table-body">
                                <tr><td colspan="5" style="text-align: center; padding: 2rem;">Loading...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    },

    async mount() {
        document.getElementById('page-title').textContent = 'Index Migrations';
        await this.loadData();
        
        // Listen for migration events
        ws.on('event:IndexMigrationStarted', () => this.loadData());
        ws.on('event:IndexMigrationFinished', () => this.loadData());
    },

    unmount() {
        ws.off('event:IndexMigrationStarted');
        ws.off('event:IndexMigrationFinished');
    },

    async loadData() {
        await Promise.all([
            this.loadVersions(),
            this.loadMigrations()
        ]);
    },
    
    async loadVersions() {
        const container = document.getElementById('active-versions-container');
        try {
            const versions = await api.getVersions();
            
            if (versions.length === 0) {
                container.innerHTML = `<div class="text-muted" style="text-align: center; padding: 1rem;">No versions defined.</div>`;
                return;
            }
            
            // Group by modality and find active
            const activeByModality = {};
            versions.forEach(v => {
                if (v.is_active) activeByModality[v.modality] = v;
            });
            
            let html = '<div style="display: flex; flex-direction: column; gap: 1rem;">';
            ['audio', 'transcript', 'metadata'].forEach(mod => {
                const v = activeByModality[mod];
                html += `
                    <div style="padding: 1rem; background: rgba(0,0,0,0.2); border: 1px solid ${v ? 'var(--status-success)' : 'var(--border-color)'}; border-radius: var(--border-radius-sm);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <span style="font-weight: 600; text-transform: capitalize;">${mod}</span>
                            ${v ? '<span class="badge badge-success">Active</span>' : '<span class="badge badge-warning">No Active</span>'}
                        </div>
                        <div style="font-size: 0.8rem; color: var(--text-secondary); font-family: monospace;">
                            ${v ? `
                                <div>Model: ${v.model_name} ${v.model_version}</div>
                                <div>Dim: ${v.dimension}</div>
                                <div>ID: ${v.id.substring(0,8)}</div>
                            ` : 'Requires configuration'}
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            
            container.innerHTML = html;
        } catch (e) {
            container.innerHTML = `<div style="color: var(--status-danger);">Failed to load versions</div>`;
        }
    },
    
    async loadMigrations() {
        const tbody = document.getElementById('migration-table-body');
        try {
            const migrations = await api.getMigrations();
            
            if (migrations.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem; color: var(--text-muted);">No migrations recorded.</td></tr>';
                return;
            }
            
            tbody.innerHTML = '';
            
            // Sort by created_at desc if available, assuming they are ordered or we just reverse
            migrations.reverse().forEach(item => {
                const badgeClass = Utils.getStatusBadgeClass(item.status);
                
                const pct = item.total_items > 0 
                    ? Math.round(((item.processed_items + item.failed_items) / item.total_items) * 100) 
                    : 0;
                    
                const progressHtml = `
                    <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.75rem; margin-bottom: 0.25rem;">
                        <span>${item.processed_items}/${item.total_items}</span>
                        <span>${pct}%</span>
                    </div>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: ${pct}%; ${item.status === 'failed' ? 'background: var(--status-danger);' : ''}"></div>
                    </div>
                `;
                
                let actionsHtml = '-';
                if (item.status === 'completed') {
                    // It's completed but maybe not switched? In this UI, completed usually means it's ready to switch or has been switched.
                    // We need to check if the target version is active to know if we should show switch button.
                    // For simplicity, we just show a switch button if it's completed.
                    actionsHtml = `
                        <button class="btn btn-primary btn-icon" onclick="MigrationPanel.switchIndex('${item.id}')" title="Switch Read Alias">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3L12 7L8 11"></path><line x1="12" y1="7" x2="3" y2="7"></line><path d="M16 21L12 17L16 13"></path><line x1="12" y1="17" x2="21" y2="17"></line></svg>
                        </button>
                    `;
                }
                
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="text-transform: capitalize;">${item.modality}</td>
                    <td style="font-family: monospace; font-size: 0.8rem;">
                        <div style="color: var(--text-secondary);">${item.from_version_id ? item.from_version_id.substring(0,8) : 'None'}</div>
                        <div>↓</div>
                        <div>${item.to_version_id.substring(0,8)}</div>
                    </td>
                    <td><span class="badge ${badgeClass}">${item.status}</span></td>
                    <td style="width: 150px;">${progressHtml}</td>
                    <td>${actionsHtml}</td>
                `;
                tbody.appendChild(tr);
            });
            
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 2rem; color: var(--status-danger);">Failed to load migrations</td></tr>`;
        }
    },
    
    showCreateVersionModal() {
        const html = `
            <form id="create-version-form" onsubmit="event.preventDefault(); MigrationPanel.submitCreateVersion();">
                <div class="form-group">
                    <label class="form-label">Modality</label>
                    <select id="cv-modality" class="form-control" required>
                        <option value="audio">Audio</option>
                        <option value="transcript">Transcript</option>
                        <option value="metadata">Metadata</option>
                    </select>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div class="form-group">
                        <label class="form-label">Model Name</label>
                        <input type="text" id="cv-model" class="form-control" value="laion/clap-htatsc-0" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Model Version</label>
                        <input type="text" id="cv-model-ver" class="form-control" value="v1" required>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Dimensions</label>
                    <input type="number" id="cv-dim" class="form-control" value="512" required>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div class="form-group">
                        <label class="form-label">Chunking Strategy</label>
                        <input type="text" id="cv-chunk-strat" class="form-control" value="fixed_duration" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Chunking Version</label>
                        <input type="text" id="cv-chunk-ver" class="form-control" value="v1" required>
                    </div>
                </div>
                <div class="form-group">
                    <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer; color: var(--text-primary); font-size: 0.9rem;">
                        <input type="checkbox" id="cv-activate" style="width: 16px; height: 16px;">
                        Set as active immediately (Development only)
                    </label>
                </div>
            </form>
        `;
        
        const footer = `
            <button class="btn btn-ghost" onclick="Utils.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="document.getElementById('create-version-form').dispatchEvent(new Event('submit'))">Save Version</button>
        `;
        
        Utils.showModal('Define Embedding Version', html, footer);
    },
    
    async submitCreateVersion() {
        const data = {
            modality: document.getElementById('cv-modality').value,
            model_name: document.getElementById('cv-model').value,
            model_version: document.getElementById('cv-model-ver').value,
            dimension: parseInt(document.getElementById('cv-dim').value, 10),
            chunking_strategy: document.getElementById('cv-chunk-strat').value,
            chunking_version: document.getElementById('cv-chunk-ver').value,
            pipeline_version: "v1",
            activate: document.getElementById('cv-activate').checked
        };
        
        try {
            const res = await api.createVersion(data);
            Utils.closeModal();
            Utils.showToast('Success', 'Version defined', 'success');
            
            if (!data.activate) {
                // Ask if they want to start migration
                if (confirm('Version created. Do you want to start backfilling data to this new version now?')) {
                    await api.startMigration(data.modality, res.id);
                    Utils.showToast('Migration Started', 'Backfill is running in background', 'info');
                }
            }
            this.loadData();
        } catch (e) {}
    },
    
    async switchIndex(migrationId) {
        if (!confirm('This will switch the active read alias for this modality in production. Proceed?')) return;
        try {
            await api.switchIndex(migrationId);
            Utils.showToast('Success', 'Traffic switched to new index', 'success');
            this.loadData();
        } catch (e) {}
    }
};
