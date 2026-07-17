/**
 * WebSocket Manager
 */

class WebSocketManager {
    constructor(path = '/ws/pipeline') {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // Need to handle both local dev and potential prod setups
        const host = window.location.host;
        this.url = `${protocol}//${host}${path}`;
        
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectDelay = 30000;
        this.handlers = {};
        
        this.statusEl = document.getElementById('ws-status');
        this.dotEl = this.statusEl?.querySelector('.status-dot');
    }

    connect() {
        if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
            return;
        }

        try {
            this.socket = new WebSocket(this.url);
            
            this.socket.onopen = this.onOpen.bind(this);
            this.socket.onmessage = this.onMessage.bind(this);
            this.socket.onclose = this.onClose.bind(this);
            this.socket.onerror = this.onError.bind(this);
        } catch (e) {
            console.error("Failed to create WebSocket:", e);
            this.scheduleReconnect();
        }
    }

    onOpen() {
        console.log("WebSocket connected");
        this.reconnectAttempts = 0;
        if (this.dotEl) {
            this.dotEl.className = 'status-dot connected';
            this.statusEl.title = 'Connected';
        }
        
        // Start heartbeat
        this.heartbeatInterval = setInterval(() => {
            if (this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
        
        this.triggerEvent('system:connected', null);
    }

    onMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'pong') return;
            
            if (data.type === 'initial_stats') {
                this.triggerEvent('system:stats', data.data);
                return;
            }
            
            if (data.type === 'domain_event') {
                const domainEvent = data.event;
                const eventType = domainEvent.event_type;
                
                // Trigger general event
                this.triggerEvent('event:all', domainEvent);
                
                // Trigger specific event
                this.triggerEvent(`event:${eventType}`, domainEvent);
            }
        } catch (e) {
            console.error("Failed to parse WS message:", e, event.data);
        }
    }

    onClose() {
        console.log("WebSocket disconnected");
        if (this.dotEl) {
            this.dotEl.className = 'status-dot disconnected';
            this.statusEl.title = 'Disconnected. Reconnecting...';
        }
        
        clearInterval(this.heartbeatInterval);
        this.scheduleReconnect();
    }

    onError(error) {
        console.error("WebSocket error:", error);
    }

    scheduleReconnect() {
        const delay = Math.min(
            1000 * Math.pow(2, this.reconnectAttempts) + (Math.random() * 1000), 
            this.maxReconnectDelay
        );
        
        console.log(`Reconnecting in ${Math.round(delay/1000)}s...`);
        this.reconnectAttempts++;
        
        setTimeout(() => this.connect(), delay);
    }

    on(eventName, callback) {
        if (!this.handlers[eventName]) {
            this.handlers[eventName] = [];
        }
        this.handlers[eventName].push(callback);
    }
    
    off(eventName, callback) {
        if (!this.handlers[eventName]) return;
        this.handlers[eventName] = this.handlers[eventName].filter(cb => cb !== callback);
    }

    triggerEvent(eventName, data) {
        const callbacks = this.handlers[eventName] || [];
        callbacks.forEach(cb => {
            try {
                cb(data);
            } catch (e) {
                console.error(`Error in WS handler for ${eventName}:`, e);
            }
        });
    }
}

const ws = new WebSocketManager();
