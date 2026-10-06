export function renderHeader(root, state, onNewRun, onCancel) {
    let el = root.querySelector('.app-header');
    if (!el) {
        el = document.createElement('header');
        el.className = 'app-header';
        root.appendChild(el);
    }
    
    const isRunning = state.currentState !== 'UNKNOWN' && state.currentState !== 'DONE' && state.currentState !== 'FAILED' && state.currentState !== 'CANCELLED';
    const isBlocked = state.pendingApproval !== null;
    const isCompleted = state.currentState === 'DONE' || state.status === 'completed';
    const isFailed = state.currentState === 'FAILED' || state.status === 'failed';
    const isCancelled = state.currentState === 'CANCELLED' || state.status === 'cancelled';
    
    let statusClass = 'running';
    let statusText = 'RUNNING';
    let statusIcon = '●';
    if (isBlocked) {
        statusClass = 'blocked';
        statusText = 'WAITING APPROVAL';
        statusIcon = '⚠️';
    } else if (isCompleted) {
        statusClass = 'done';
        statusText = 'COMPLETED';
        statusIcon = '✓';
    } else if (isFailed) {
        statusClass = 'failed';
        statusText = 'FAILED';
        statusIcon = '✗';
    } else if (isCancelled) {
        statusClass = 'failed';
        statusText = 'CANCELLED';
        statusIcon = '⊘';
    } else if (!isRunning) {
        statusClass = 'standby';
        statusText = 'STANDBY';
        statusIcon = '○';
    }

    // Format elapsed time
    let elapsedStr = '00:00';
    if (state.startTime) {
        const end = state.endTime || Date.now();
        const diffMs = Math.max(0, end - state.startTime);
        const secs = Math.floor(diffMs / 1000);
        const mins = Math.floor(secs / 60);
        const remSecs = secs % 60;
        elapsedStr = `${String(mins).padStart(2, '0')}:${String(remSecs).padStart(2, '0')}`;
    }

    const stepCount = state.steps ? state.steps.length : 0;
    const maxSteps = state.contract?.max_steps || state.budget?.maxSteps || 40;

    el.innerHTML = `
        <div class="brand">
            <span class="brand-icon">⚡</span>
            <span class="brand-title">AI TASK WORKER</span>
            <span class="brand-badge">CONSOLE V3</span>
        </div>
        <div class="header-right-controls">
            <div class="header-status-badge ${statusClass}">
                <span class="status-indicator-dot">${statusIcon}</span>
                <span class="status-indicator-label">${statusText}</span>
            </div>
            
            ${state.startTime ? `
                <div class="header-metric-pill" title="Elapsed Execution Time">
                    <span style="opacity:0.6;">⏱️</span>
                    <span>${elapsedStr}</span>
                </div>
            ` : ''}

            ${stepCount > 0 || isRunning ? `
                <div class="header-metric-pill" title="Executed Steps">
                    <span style="opacity:0.6;">⚡</span>
                    <span>Steps: <strong>${stepCount}</strong>/${maxSteps}</span>
                </div>
            ` : ''}

            ${isRunning && onCancel ? `
                <button class="btn-header-stop" id="btn-header-stop" title="Stop execution">
                    ⏹ Stop
                </button>
            ` : ''}

            ${(isRunning || isCompleted || isFailed || isCancelled) ? `
                <button class="btn-header-new" id="btn-new-task">
                    + New Task
                </button>
            ` : ''}
        </div>
    `;

    const newBtn = el.querySelector('#btn-new-task');
    if (newBtn && onNewRun) {
        newBtn.onclick = onNewRun;
    }

    const stopBtn = el.querySelector('#btn-header-stop');
    if (stopBtn && onCancel) {
        stopBtn.onclick = onCancel;
    }
}

