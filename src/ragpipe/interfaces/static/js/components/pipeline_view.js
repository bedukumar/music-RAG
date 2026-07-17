/**
 * Pipeline View Component (Real-time tracking)
 */

const PipelineView = {
    render() {
        return `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem;">
                <div>
                    <button class="btn btn-ghost" style="padding-left: 0; margin-bottom: 1rem;" onclick="app.navigate('media')">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
                        Back to Library
                    </button>
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <h2 id="pv-title" style="font-size: 2rem; margin: 0;">Loading...</h2>
                        <span id="pv-type-badge" class="badge">...</span>
                    </div>
                    <div id="pv-id" style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.25rem;"></div>
                </div>
                <div style="display: flex; gap: 0.5rem;">
                    <button class="btn btn-primary" onclick="PipelineView.processAllPending()">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                        Process Pending
                    </button>
                </div>
            </div>

            <div class="card" style="margin-bottom: 2rem;">
                <h3 style="margin-bottom: 1.5rem; color: var(--text-secondary);">Modality Pipelines</h3>
                <div id="pv-pipelines-container">
                    <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
                        <div class="spinner" style="margin: 0 auto 1rem auto;"></div>
                        Loading pipeline status...
                    </div>
                </div>
            </div>
        `;
    },

    mediaId: null,

    async mount(params) {
        this.mediaId = params?.id;
        if (!this.mediaId) {
            app.navigate('media');
            return;
        }
        
        document.getElementById('page-title').textContent = 'Pipeline Monitor';
        
        await this.loadStatus();
        
        // Listen for real-time updates for this specific media
        ws.on('event:all', this.handleWsEvent.bind(this));
    },

    unmount() {
        ws.off('event:all', this.handleWsEvent.bind(this));
    },

    async loadStatus() {
        try {
            const status = await api.getPipelineStatus(this.mediaId);
            this.renderStatus(status);
        } catch (e) {
            const container = document.getElementById('pv-pipelines-container');
            if (container) container.innerHTML = `<div style="text-align: center; color: var(--status-danger); padding: 2rem;">Failed to load pipeline status</div>`;
        }
    },
    
    handleWsEvent(event) {
        // Re-load if event pertains to our media ID
        if (event.payload && event.payload.media_id === this.mediaId) {
            // Debounce to prevent flashing on rapid events
            if (!this.debouncedLoad) {
                this.debouncedLoad = Utils.debounce(() => this.loadStatus(), 300);
            }
            this.debouncedLoad();
        }
    },
    
    renderStatus(data) {
        document.getElementById('pv-title').textContent = data.title || 'Unknown Title';
        document.getElementById('pv-id').textContent = `ID: ${data.media_id}`;
        
        const typeBadge = document.getElementById('pv-type-badge');
        typeBadge.textContent = data.media_type;
        typeBadge.className = `badge badge-info`;
        
        const container = document.getElementById('pv-pipelines-container');
        container.innerHTML = '';
        
        const modalities = ['audio', 'transcript', 'metadata'];
        const stageOrder = ['VALIDATION', 'NORMALIZATION', 'PREPROCESSING', 'CHUNKING', 'EMBEDDING', 'POST_PROCESSING', 'VECTOR_STORAGE'];
        
        modalities.forEach(modality => {
            const mStatus = data.modality_statuses?.find(s => s.modality === modality);
            const pState = data.pipelines?.[modality];
            
            // Build Modality Header
            const headerHtml = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <span style="font-size: 1.25rem; font-weight: 600; text-transform: capitalize;">${modality}</span>
                        ${mStatus ? `<span class="badge ${Utils.getStatusBadgeClass(mStatus.embedding_status)}">${mStatus.embedding_status}</span>` : '<span class="badge badge-skipped">N/A</span>'}
                        ${!mStatus?.data_available ? `<span class="badge badge-warning">No Data</span>` : ''}
                    </div>
                    <div style="display: flex; gap: 0.5rem;">
                        <button class="btn btn-outline btn-icon" onclick="PipelineView.reprocess('${modality}')" title="Force Reprocess" ${!mStatus?.data_available ? 'disabled' : ''}>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
                        </button>
                    </div>
                </div>
            `;
            
            let pipelineHtml = '';
            
            if (pState && pState.stages && pState.stages.length > 0) {
                // Build Timeline
                let timelineHtml = '<div class="timeline">';
                
                stageOrder.forEach((stageName) => {
                    const stageResult = pState.stages.find(s => s.stage === stageName);
                    
                    let statusClass = '';
                    let iconHtml = '';
                    let durationHtml = '';
                    
                    if (!stageResult || stageResult.status === 'pending') {
                        statusClass = 'pending';
                        iconHtml = '<circle cx="12" cy="12" r="4" fill="currentColor"></circle>';
                    } else if (stageResult.status === 'running') {
                        statusClass = 'running';
                        iconHtml = '<path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" stroke-width="2" stroke-linecap="round"></path>';
                    } else if (stageResult.status === 'completed') {
                        statusClass = 'completed';
                        iconHtml = '<polyline points="20 6 9 17 4 12" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></polyline>';
                        if (stageResult.duration_ms) {
                            durationHtml = `<div style="font-size: 0.65rem; color: var(--text-muted); margin-top: 2px;">${Utils.formatDuration(stageResult.duration_ms)}</div>`;
                        }
                    } else if (stageResult.status === 'failed') {
                        statusClass = 'failed';
                        iconHtml = '<line x1="18" y1="6" x2="6" y2="18" stroke-width="2" stroke-linecap="round"></line><line x1="6" y1="6" x2="18" y2="18" stroke-width="2" stroke-linecap="round"></line>';
                    }
                    
                    const prettyName = stageName.replace('_', ' ');
                    
                    timelineHtml += `
                        <div class="timeline-step ${statusClass}" title="${stageName}">
                            <div class="step-circle">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">${iconHtml}</svg>
                            </div>
                            <div class="step-label">${prettyName}</div>
                            ${durationHtml}
                        </div>
                    `;
                });
                
                timelineHtml += '</div>';
                
                // Add error message if failed
                if (pState.overall_status === 'failed') {
                    const failedStage = pState.stages.find(s => s.status === 'failed');
                    if (failedStage && failedStage.error_message) {
                        timelineHtml += `
                            <div style="margin-top: 1rem; padding: 1rem; background: rgba(239, 68, 68, 0.1); border-left: 3px solid var(--status-danger); border-radius: 4px;">
                                <div style="color: var(--status-danger); font-weight: 600; font-size: 0.85rem;">Error at ${failedStage.stage}</div>
                                <div style="font-size: 0.85rem; margin-top: 0.5rem; font-family: monospace;">${Utils.escapeHtml(failedStage.error_message)}</div>
                            </div>
                        `;
                    }
                }
                
                pipelineHtml = timelineHtml;
            } else {
                pipelineHtml = `
                    <div style="padding: 2rem; background: rgba(0,0,0,0.2); border-radius: var(--border-radius-sm); text-align: center; color: var(--text-muted);">
                        No pipeline execution history found for this modality.
                    </div>
                `;
            }
            
            const section = document.createElement('div');
            section.style.marginBottom = '2.5rem';
            section.style.paddingBottom = '2.5rem';
            section.style.borderBottom = '1px solid var(--border-color)';
            
            section.innerHTML = headerHtml + pipelineHtml;
            container.appendChild(section);
        });
        
        // Remove last border bottom
        if (container.lastChild) {
            container.lastChild.style.borderBottom = 'none';
            container.lastChild.style.marginBottom = '0';
            container.lastChild.style.paddingBottom = '0';
        }
    },
    
    async processAllPending() {
        try {
            await api.processMedia(this.mediaId);
            Utils.showToast('Triggered', 'Processing started for pending modalities.', 'info');
        } catch(e) {}
    },
    
    async reprocess(modality) {
        if (!confirm(`Are you sure you want to force reprocess ${modality}? This will delete existing vectors.`)) return;
        try {
            await api.reprocessModality(this.mediaId, modality);
            Utils.showToast('Triggered', `Reprocessing started for ${modality}.`, 'info');
        } catch(e) {}
    }
};
