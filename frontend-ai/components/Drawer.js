export function renderDrawer(root, state, onClose) {
    let el = root.querySelector('.inspector-drawer-overlay');
    if (!state.inspectorData) {
        if (el) el.remove();
        return;
    }
    
    if (!el) {
        el = document.createElement('div');
        el.className = 'inspector-drawer-overlay';
        root.appendChild(el);
    }
    
    const data = state.inspectorData || {};
    const title = data.title || 'Action Inspector';
    const facet = data.facet || 'ACT';
    const tool = data.tool || '';
    let status = data.status || 'SUCCESS';
    const duration = data.duration || '';
    const input = data.input || null;
    const output = data.output !== undefined ? data.output : null;
    const evidence = data.evidence || null;

    // Detect if the output itself is an error / failure
    const rawOutStr = typeof output === 'string' ? output : JSON.stringify(output || '');
    const hasErrorContent = rawOutStr.includes('Failed:') || rawOutStr.includes('Error:') || rawOutStr.includes('no such column') || rawOutStr.includes('429') || rawOutStr.includes('Rate Limit');
    if (hasErrorContent && status === 'SUCCESS') {
        status = 'FAILED (SQL Error)';
    }

    const isError = status.toLowerCase().includes('fail') || status.toLowerCase().includes('error') || status.toLowerCase().includes('reject') || hasErrorContent;

    let formattedOutput = '';
    if (output !== null && typeof output === 'object') {
        try {
            formattedOutput = JSON.stringify(output, null, 2);
        } catch {
            formattedOutput = String(output);
        }
    } else if (typeof output === 'string') {
        try {
            // Try formatting if it is stringified JSON
            const parsed = JSON.parse(output);
            formattedOutput = JSON.stringify(parsed, null, 2);
        } catch {
            formattedOutput = output;
        }
    } else {
        formattedOutput = String(output || 'No output payload available.');
    }

    let formattedInput = '';
    if (input) {
        try {
            formattedInput = JSON.stringify(input, null, 2);
        } catch {
            formattedInput = String(input);
        }
    }

    el.innerHTML = `
        <div class="inspector-drawer-panel">
            <div class="inspector-drawer-header">
                <div class="inspector-title-group">
                    <span class="inspector-facet-pill ${facet.toLowerCase()}">${escapeHtml(facet)}</span>
                    <h3 class="inspector-drawer-title">${escapeHtml(title)}</h3>
                </div>
                <button class="btn-drawer-close" id="btn-close-drawer" title="Close Drawer">✕</button>
            </div>
            
            <div class="inspector-drawer-meta-bar">
                ${tool ? `<div class="drawer-meta-item"><strong>Tool:</strong> <code>${escapeHtml(tool)}</code></div>` : ''}
                <div class="drawer-meta-item"><strong>Status:</strong> <span class="badge-status ${isError ? 'bad' : 'good'}">${escapeHtml(status)}</span></div>
                ${duration ? `<div class="drawer-meta-item"><strong>Duration:</strong> <span>${escapeHtml(duration)}</span></div>` : ''}
            </div>

            <div class="inspector-drawer-body scrollable-drawer-content">
                ${formattedInput ? `
                    <div class="drawer-section">
                        <div class="drawer-section-heading">Input Parameters</div>
                        <pre class="code-block-viewer">${escapeHtml(formattedInput)}</pre>
                    </div>
                ` : ''}

                <div class="drawer-section">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <div class="drawer-section-heading">${facet === 'VERIFY' ? 'Live Database Evidence & State Observation' : 'Response & Execution Output'}</div>
                        <button class="btn-copy-code" id="btn-copy-payload">📋 Copy</button>
                    </div>
                    <pre class="code-block-viewer main-output">${escapeHtml(formattedOutput)}</pre>
                </div>

                ${evidence ? `
                    <div class="drawer-section">
                        <div class="drawer-section-heading">${facet === 'VERIFY' ? 'Evaluator Verification & Compliance Checklist' : 'Deterministic Verifier Details'}</div>
                        <div class="verifier-callout">
                            ${escapeHtml(typeof evidence === 'object' ? JSON.stringify(evidence, null, 2) : String(evidence))}
                        </div>
                    </div>
                ` : ''}
            </div>

            <div class="inspector-drawer-footer">
                <button class="btn-primary-compact" id="btn-footer-close">Close Inspector</button>
            </div>
        </div>
    `;

    // Event listeners
    const closeBtn = el.querySelector('#btn-close-drawer');
    const footerCloseBtn = el.querySelector('#btn-footer-close');
    const handleClose = (e) => {
        e.stopPropagation();
        if (onClose) onClose();
    };
    if (closeBtn) closeBtn.onclick = handleClose;
    if (footerCloseBtn) footerCloseBtn.onclick = handleClose;

    // Click outside panel to close
    el.onclick = (e) => {
        if (e.target === el) {
            if (onClose) onClose();
        }
    };

    const copyBtn = el.querySelector('#btn-copy-payload');
    if (copyBtn) {
        copyBtn.onclick = (e) => {
            e.stopPropagation();
            navigator.clipboard.writeText(formattedOutput);
            copyBtn.textContent = '✓ Copied!';
            setTimeout(() => { copyBtn.textContent = '📋 Copy'; }, 2000);
        };
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

