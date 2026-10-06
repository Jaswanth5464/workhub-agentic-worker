import { config } from './config.js';

export class ApiClient {
    constructor() {
        this.baseUrl = config.apiBaseUrl;
        this.source = null;
        this.reconnectAttempts = 0;
        this.lastSeq = null;
    }

    async getRuns() {
        const res = await fetch(`${this.baseUrl}/api/runs`);
        return res.json();
    }

    async cancelRun(runId) {
        if (!runId) return;
        try {
            await fetch(`${this.baseUrl}/api/runs/${runId}`, { method: 'DELETE' });
        } catch (e) {
            console.error("Cancel run failed", e);
        }
    }

    async approveAction(runId, decision, userResponse = "") {
        if (!runId) return;
        try {
            const res = await fetch(`${this.baseUrl}/api/runs/${runId}/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ approved: Boolean(decision), user_response: userResponse || "" })
            });
            return res.json();
        } catch (e) {
            console.error("Approve action failed", e);
        }
    }

    connectStream(runId, onEvent, onStatus) {
        if (this.source) {
            this.source.close();
            this.source = null;
        }
        
        let url = `${this.baseUrl}/api/runs/${runId}/stream`;
        if (this.lastSeq !== null) {
            url += `?after=${this.lastSeq}`;
        }
        
        this.source = new EventSource(url);
        
        this.source.onopen = () => {
            this.reconnectAttempts = 0;
            if (onStatus) onStatus('connected');
        };

        this.source.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data.seq !== undefined) {
                    this.lastSeq = data.seq;
                }
                if (onEvent) onEvent(data);
                if (data.type === 'run_completed' && this.source) {
                    this.source.close();
                    this.source = null;
                }
            } catch (err) {
                console.error("Error parsing event stream message", err);
            }
        };

        this.source.onerror = (e) => {
            if (this.source) {
                this.source.close();
                this.source = null;
            }
            if (onStatus) onStatus('closed');
        };
    }
}
