import { reducer, initialState } from './store.js';
import { adaptEvent } from './adapter.js';
import { ApiClient } from './api.js';

import { renderHeader } from './components/Header.js';
import { renderFlow } from './components/Flow.js';
import { renderEmptyState } from './components/EmptyState.js';
import { renderDrawer } from './components/Drawer.js';

let state = initialState();
const api = new ApiClient();

function dispatch(event) {
    state = reducer(state, event);
    render();
}

// Timer tick for live elapsed time updates
setInterval(() => {
    const isRunning = state.currentState !== 'UNKNOWN' && state.currentState !== 'DONE' && state.currentState !== 'FAILED' && state.currentState !== 'CANCELLED';
    if (isRunning && state.startTime) {
        renderHeader(document.getElementById('header-root'), state, handleReset, handleCancel);
    }
}, 1000);

async function handleNewTask(taskText) {
    console.log("Starting new task:", taskText);
    dispatch({ type: 'task_started', task: taskText });
    dispatch({ type: 'state', state: 'UNDERSTANDING' });
    
    try {
        const res = await fetch(`${api.baseUrl}/api/runs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task: taskText })
        });
        
        const data = await res.json();
        
        if (data.run_id) {
            dispatch({ type: 'task_started', task: taskText, runId: data.run_id });
            api.connectStream(
                data.run_id,
                async (event) => {
                    const adapted = await adaptEvent(event, state.steps.length);
                    if (adapted) dispatch(adapted);
                },
                (status) => console.log('SSE Stream status:', status)
            );
        }
    } catch (e) {
        console.error("Failed to start run", e);
        dispatch({ type: 'state', state: 'FAILED' });
    }
}

async function handleApprove(decision, reason = "") {
    if (!state.runId) return;
    try {
        await api.approveAction(state.runId, decision, reason);
        dispatch({ type: 'approval_resolved' });
    } catch (e) {
        console.error("Approval submission failed", e);
    }
}

async function handleCancel() {
    if (!state.runId) return;
    try {
        await api.cancelRun(state.runId);
        dispatch({ type: 'state', state: 'CANCELLED' });
        dispatch({ type: 'run_completed', status: 'cancelled', final_answer: 'Run was cancelled by human operator.' });
    } catch (e) {
        console.error("Cancel failed", e);
    }
}

function handleReset() {
    state = initialState();
    render();
}

function handleOpenInspector(data) {
    dispatch({ type: 'open_inspector', data });
}

function handleCloseInspector() {
    dispatch({ type: 'close_inspector' });
}

function render() {
    const app = document.getElementById('app');
    app.className = 'app-container';
    
    // Header
    const headerRoot = document.getElementById('header-root') || createRoot('header-root', app);
    renderHeader(headerRoot, state, handleReset, handleCancel);
    
    const isRunning = state.currentState !== 'UNKNOWN' || state.steps.length > 0 || state.task;
    
    if (!isRunning) {
        // Show empty state prompt
        const emptyRoot = document.getElementById('empty-root') || createRoot('empty-root', app);
        emptyRoot.style.display = 'block';
        renderEmptyState(emptyRoot, handleNewTask);
        
        ['workspace-root'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
    } else {
        // Hide empty state prompt
        const emptyRoot = document.getElementById('empty-root');
        if (emptyRoot) emptyRoot.style.display = 'none';
        
        // Unified Full-Width Console
        let workspaceRoot = document.getElementById('workspace-root');
        if (!workspaceRoot) {
            workspaceRoot = createRoot('workspace-root', app);
            workspaceRoot.className = 'workspace-unified-container';
            
            const mainStream = document.createElement('div');
            mainStream.id = 'flow-root';
            mainStream.className = 'main-stream-unified';
            workspaceRoot.appendChild(mainStream);
        }
        workspaceRoot.style.display = 'flex';
        
        const flowRoot = document.getElementById('flow-root');
        if (flowRoot) {
            renderFlow(flowRoot, state, {
                onApprove: handleApprove,
                onCancel: handleCancel,
                onOpenInspector: handleOpenInspector
            });
        }
    }

    // Right-Side Inspector Drawer
    const drawerRoot = document.getElementById('drawer-root') || createRoot('drawer-root', app);
    renderDrawer(drawerRoot, state, handleCloseInspector);
}

function createRoot(id, parent) {
    const el = document.createElement('div');
    el.id = id;
    parent.appendChild(el);
    return el;
}

// Initial render
render();

