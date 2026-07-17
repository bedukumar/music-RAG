/**
 * Main Application Logic
 */

class App {
    constructor() {
        this.currentView = null;
        this.currentViewName = '';
        this.container = document.getElementById('view-container');
        
        // Define route mappings
        this.routes = {
            'dashboard': Dashboard,
            'media': MediaTable,
            'pipeline': PipelineView,
            'jobs': JobList,
            'migrations': MigrationPanel
        };
        
        this.init();
    }
    
    async init() {
        // Connect WS
        ws.connect();
        
        // Setup navigation listeners
        document.querySelectorAll('.nav-item').forEach(el => {
            el.addEventListener('click', (e) => {
                const view = e.currentTarget.getAttribute('data-view');
                if (view) {
                    e.preventDefault();
                    this.navigate(view);
                }
            });
        });
        
        // Handle refresh button
        document.getElementById('btn-refresh')?.addEventListener('click', () => {
            if (this.currentView && typeof this.currentView.mount === 'function') {
                this.currentView.mount(this.currentParams);
                
                // Add spin animation to icon
                const icon = document.querySelector('#btn-refresh svg');
                icon.style.animation = 'spin 0.5s ease-out';
                setTimeout(() => icon.style.animation = 'none', 500);
            }
        });
        
        // Handle initial route
        const hash = window.location.hash.substring(1);
        if (hash) {
            const parts = hash.split('/');
            const route = parts[0];
            const param = parts[1];
            if (this.routes[route]) {
                await this.navigate(route, param, false);
                return;
            }
        }
        
        // Default route
        await this.navigate('dashboard');
    }
    
    async navigate(viewName, params = null, updateHash = true) {
        if (!this.routes[viewName]) {
            console.error(`Route ${viewName} not found`);
            return;
        }
        
        // Unmount current view
        if (this.currentView && typeof this.currentView.unmount === 'function') {
            this.currentView.unmount();
        }
        
        // Update nav UI
        document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
        const navEl = document.querySelector(`.nav-item[data-view="${viewName === 'pipeline' ? 'media' : viewName}"]`);
        if (navEl) navEl.classList.add('active');
        
        // Update hash
        if (updateHash) {
            window.location.hash = params ? `${viewName}/${params}` : viewName;
        }
        
        this.currentViewName = viewName;
        this.currentView = this.routes[viewName];
        this.currentParams = params ? { id: params } : null;
        
        // Render and mount new view
        this.container.innerHTML = this.currentView.render();
        
        if (typeof this.currentView.mount === 'function') {
            await this.currentView.mount(this.currentParams);
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
