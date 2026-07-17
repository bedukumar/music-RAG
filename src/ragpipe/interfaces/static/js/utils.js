/**
 * Utility Functions
 */

const Utils = {
    formatDate(isoString) {
        if (!isoString) return '-';
        const date = new Date(isoString);
        return date.toLocaleString();
    },

    formatDuration(ms) {
        if (ms === null || ms === undefined) return '-';
        if (ms < 1000) return `${Math.round(ms)}ms`;
        const s = ms / 1000;
        if (s < 60) return `${s.toFixed(1)}s`;
        const m = Math.floor(s / 60);
        const rs = Math.round(s % 60);
        return `${m}m ${rs}s`;
    },

    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
             .toString()
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    },

    createElement(html) {
        const template = document.createElement('template');
        template.innerHTML = html.trim();
        return template.content.firstChild;
    },

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    getStatusBadgeClass(status) {
        switch(status?.toLowerCase()) {
            case 'completed': return 'badge-success';
            case 'processing': 
            case 'running': return 'badge-warning';
            case 'failed': return 'badge-danger';
            case 'pending': return 'badge-pending';
            default: return 'badge-info';
        }
    },
    
    getModalityIconClass(status) {
        return status?.toLowerCase() || 'skipped';
    },
    
    getModalityLetter(modality) {
        switch(modality?.toLowerCase()) {
            case 'audio': return 'A';
            case 'transcript': return 'T';
            case 'metadata': return 'M';
            default: return '?';
        }
    },

    showToast(title, message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const id = 'toast-' + Math.random().toString(36).substr(2, 9);
        
        // Define icons based on type
        const icons = {
            success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
            error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
            warning: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
            info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
        };

        const toastHtml = `
            <div id="${id}" class="toast ${type}">
                <div class="toast-icon">${icons[type]}</div>
                <div class="toast-content">
                    <h4>${this.escapeHtml(title)}</h4>
                    <p>${this.escapeHtml(message)}</p>
                </div>
                <button class="toast-close" onclick="document.getElementById('${id}').remove()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </button>
            </div>
        `;

        const toastEl = this.createElement(toastHtml);
        container.appendChild(toastEl);

        setTimeout(() => {
            const el = document.getElementById(id);
            if (el) {
                el.style.animation = 'fadeOut 0.3s forwards';
                setTimeout(() => el.remove(), 300);
            }
        }, 5000);
    },
    
    showModal(title, contentHtml, footerHtml = '') {
        const container = document.getElementById('modal-container');
        
        const modalHtml = `
            <div class="modal-overlay active" id="current-modal">
                <div class="modal">
                    <div class="modal-header">
                        <h3>${title}</h3>
                        <button class="btn-icon btn-ghost" onclick="Utils.closeModal()">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        </button>
                    </div>
                    <div class="modal-body">
                        ${contentHtml}
                    </div>
                    ${footerHtml ? `<div class="modal-footer">${footerHtml}</div>` : ''}
                </div>
            </div>
        `;
        
        container.innerHTML = '';
        container.appendChild(this.createElement(modalHtml));
    },
    
    closeModal() {
        const modal = document.getElementById('current-modal');
        if (modal) {
            modal.classList.remove('active');
            setTimeout(() => modal.remove(), 300);
        }
    }
};
