export function renderRunBar(root, state, onCancel) {
    let el = root.querySelector('.run-bar');
    if (!el) {
        el = document.createElement('div');
        el.className = 'run-bar';
        root.appendChild(el);
    }
    
    const stepCount = state.steps.length;
    const taskTitle = state.task || 'Active Task Execution';
    const isRunning = state.currentState !== 'DONE' && state.currentState !== 'FAILED' && state.status !== 'completed';
    const isPending = state.pendingApproval !== null;

    el.innerHTML = `
        <div class="task-title-container">
            <span class="task-icon">⚡</span>
            <div class="task-title-text" title="${escapeHtml(taskTitle)}">
                ${escapeHtml(taskTitle)}
            </div>
            <button class="btn-show-more-prompt" id="btn-runbar-show-more" title="View complete task instructions">
                Show more ▾
            </button>
        </div>
        <div class="run-stats">
            <span class="status-badge" style="${isPending ? 'background: var(--color-warn-soft); color: var(--color-warn); border-color: var(--color-warn-border);' : ''}">
                ${isPending ? '⚠️ Action Paused (Approval Required)' : `● Step ${stepCount}`}
            </span>
            ${isRunning ? `
                <button class="btn-cancel" id="btn-cancel-run">Cancel Run</button>
            ` : ''}
        </div>
    `;

    const cancelBtn = el.querySelector('#btn-cancel-run');
    if (cancelBtn && onCancel) {
        cancelBtn.onclick = onCancel;
    }

    const showMoreBtn = el.querySelector('#btn-runbar-show-more');
    if (showMoreBtn) {
        showMoreBtn.onclick = () => openPromptModal(taskTitle);
    }
}

export function openPromptModal(promptText) {
    let modal = document.getElementById('task-prompt-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'task-prompt-modal';
        modal.className = 'prompt-modal-overlay';
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
        <div class="prompt-modal-card">
            <div class="prompt-modal-header">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:16px;">📋</span>
                    <strong style="font-size:14px; color:var(--color-ink);">Full Task Prompt & Objectives</strong>
                </div>
                <button class="prompt-modal-close" id="btn-modal-close" title="Close">✕</button>
            </div>
            <div class="prompt-modal-content">
                ${escapeHtml(promptText || 'No prompt specified.')}
            </div>
        </div>
    `;

    modal.style.display = 'flex';

    const closeBtn = modal.querySelector('#btn-modal-close');
    if (closeBtn) {
        closeBtn.onclick = () => { modal.style.display = 'none'; };
    }

    modal.onclick = (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    };
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

