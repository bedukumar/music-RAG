/**
 * Dashboard Component
 */

const Dashboard = {
    render() {
        return `
            <div class="dashboard-grid">
                <div class="card stat-card">
                    <div class="stat-icon" style="color: #3b82f6;">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
                    </div>
                    <div class="stat-info">
                        <h3 id="stat-total-media">-</h3>
                        <p>Total Media Items</p>
                    </div>
                </div>
                
                <div class="card stat-card">
                    <div class="stat-icon" style="color: #f59e0b;">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                    </div>
                    <div class="stat-info">
                        <h3 id="stat-active-jobs">-</h3>
                        <p>Active Processing Jobs</p>
                    </div>
                </div>
                
                <div class="card stat-card">
                    <div class="stat-icon" style="color: #ef4444;">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                    </div>
                    <div class="stat-info">
                        <h3 id="stat-failed-jobs">-</h3>
                        <p>Failed Jobs</p>
                    </div>
                </div>
                
                <div class="card stat-card">
                    <div class="stat-icon" style="color: #10b981;">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    </div>
                    <div class="stat-info">
                        <h3 id="stat-completed-jobs">-</h3>
                        <p>Completed Jobs</p>
                    </div>
                </div>
            </div>
            
            <div class="dashboard-grid">
                <div class="card" style="grid-column: span 2;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                        <h3 style="font-size: 1.1rem; color: var(--text-secondary);">Recent Events</h3>
                        <button class="btn btn-ghost btn-icon" onclick="Dashboard.clearEvents()" title="Clear">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                        </button>
                    </div>
                    <div id="event-feed" style="max-height: 400px; overflow-y: auto; display: flex; flex-direction: column; gap: 0.75rem;">
                        <div class="text-muted" style="text-align: center; padding: 2rem;">Waiting for events...</div>
                    </div>
                </div>
                
                <div class="card">
                    <h3 style="font-size: 1.1rem; color: var(--text-secondary); margin-bottom: 1.5rem;">System Health</h3>
                    <div style="display: flex; flex-direction: column; gap: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>API Status</span>
                            <span class="badge badge-success">Online</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>Database</span>
                            <span class="badge badge-success">Connected</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>Vector Store</span>
                            <span class="badge badge-success">Connected</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>WebSocket</span>
                            <span id="health-ws" class="badge badge-warning">Connecting...</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    async mount() {
        document.getElementById('page-title').textContent = 'Dashboard';
        
        // Initial load
        await this.loadStats();
        
        // Listen for stats updates via WS
        ws.on('system:stats', this.updateStats.bind(this));
        
        // Listen for all events to populate feed
        ws.on('event:all', this.addEventToFeed.bind(this));
        
        // Update WS health badge
        const wsHealth = document.getElementById('health-ws');
        if (wsHealth) {
            if (ws.socket && ws.socket.readyState === WebSocket.OPEN) {
                wsHealth.className = 'badge badge-success';
                wsHealth.textContent = 'Connected';
            } else {
                wsHealth.className = 'badge badge-danger';
                wsHealth.textContent = 'Disconnected';
            }
        }
        
        ws.on('system:connected', () => {
            const el = document.getElementById('health-ws');
            if (el) {
                el.className = 'badge badge-success';
                el.textContent = 'Connected';
            }
        });
    },

    unmount() {
        ws.off('system:stats', this.updateStats.bind(this));
        ws.off('event:all', this.addEventToFeed.bind(this));
    },

    async loadStats() {
        try {
            const stats = await api.getSystemStats();
            this.updateStats(stats);
        } catch (e) {
            // Error handled by API client
        }
    },

    updateStats(stats) {
        if (!stats) return;
        
        const totalEl = document.getElementById('stat-total-media');
        const activeEl = document.getElementById('stat-active-jobs');
        const failedEl = document.getElementById('stat-failed-jobs');
        const completedEl = document.getElementById('stat-completed-jobs');
        
        if (totalEl) totalEl.textContent = stats.total_media || 0;
        if (activeEl && stats.jobs) {
            activeEl.textContent = (stats.jobs.pending || 0) + (stats.jobs.processing || 0);
        }
        if (failedEl && stats.jobs) failedEl.textContent = stats.jobs.failed || 0;
        if (completedEl && stats.jobs) completedEl.textContent = stats.jobs.completed || 0;
    },
    
    addEventToFeed(event) {
        const feed = document.getElementById('event-feed');
        if (!feed) return;
        
        // Remove empty state message if it exists
        if (feed.children.length === 1 && feed.children[0].classList.contains('text-muted')) {
            feed.innerHTML = '';
        }
        
        let icon = '⚡';
        let color = 'var(--text-primary)';
        
        if (event.event_type.includes('Failed')) {
            icon = '❌';
            color = 'var(--status-danger)';
        } else if (event.event_type.includes('Completed') || event.event_type.includes('Finished')) {
            icon = '✅';
            color = 'var(--status-success)';
        } else if (event.event_type.includes('Started') || event.event_type.includes('Created')) {
            icon = '🚀';
            color = 'var(--status-info)';
        }
        
        const time = new Date(event.timestamp).toLocaleTimeString();
        
        const eventHtml = `
            <div style="display: flex; gap: 1rem; padding: 0.75rem; background: rgba(0,0,0,0.2); border-radius: var(--border-radius-sm); border-left: 2px solid ${color};">
                <div style="font-size: 1.2rem;">${icon}</div>
                <div style="flex: 1;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                        <span style="font-weight: 500; color: ${color};">${event.event_type}</span>
                        <span style="font-size: 0.75rem; color: var(--text-muted);">${time}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); word-break: break-all;">
                        Media ID: <a href="javascript:void(0)" onclick="app.navigate('pipeline', '${event.payload.media_id}')" style="color: #8b5cf6;">${event.payload.media_id?.substring(0,8) || 'N/A'}</a>
                        ${event.payload.modality ? ` | Modality: ${event.payload.modality}` : ''}
                        ${event.payload.stage ? ` | Stage: ${event.payload.stage}` : ''}
                        ${event.payload.error ? `<br><span style="color: var(--status-danger);">${event.payload.error}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
        
        const el = Utils.createElement(eventHtml);
        feed.insertBefore(el, feed.firstChild);
        
        // Keep max 50 items
        if (feed.children.length > 50) {
            feed.removeChild(feed.lastChild);
        }
    },
    
    clearEvents() {
        const feed = document.getElementById('event-feed');
        if (feed) {
            feed.innerHTML = '<div class="text-muted" style="text-align: center; padding: 2rem;">Waiting for events...</div>';
        }
    }
};
