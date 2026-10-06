export function renderEmptyState(root, onSubmit) {
    let el = root.querySelector('.empty-state-wrapper');
    if (!el) {
        el = document.createElement('div');
        el.className = 'empty-state-wrapper';
        root.appendChild(el);
    }
    
    el.innerHTML = `
        <h2>Assign a Task to AI Agent</h2>
        <div class="empty-subtitle">The agent executes through strict security guards with human authorization for mutations.</div>
        <textarea id="task-input" class="task-input-box" placeholder="e.g. Find all engineering employees with their current salary, or raise the salary of Engineering employees by 10%..."></textarea>
        
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <button id="btn-submit" class="btn-execute">⚡ Execute Task</button>
            <span style="font-size:12px; color:var(--color-muted);">🛡️ Guard Mode: Strict HITL</span>
        </div>

        <div style="margin-top:28px;">
            <div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:var(--color-muted); margin-bottom:10px;">
                💡 Quick Example Scenarios
            </div>
            <div class="preset-pills">
                <button class="preset-chip" data-prompt="Find Jane Smith's email address and department.">🔍 Find Employee Info</button>
                <button class="preset-chip" data-prompt="List all pending expense reports and their total amount.">📊 Audit Pending Expenses</button>
                <button class="preset-chip" data-prompt="Raise the salary of all Engineering employees by 10%.">⚠️ Alter Engineering Salaries (HITL Approval)</button>
                <button class="preset-chip" data-prompt="Audit all pending tasks and summarize them by priority.">📋 Audit Company Tasks</button>
            </div>
        </div>
    `;
    
    const input = el.querySelector('#task-input');
    const submitBtn = el.querySelector('#btn-submit');
    
    submitBtn.onclick = () => {
        if (input.value.trim()) {
            onSubmit(input.value.trim());
        }
    };
    
    input.onkeydown = (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            if (input.value.trim()) {
                onSubmit(input.value.trim());
            }
        }
    };

    el.querySelectorAll('.preset-chip').forEach(chip => {
        chip.onclick = () => {
            input.value = chip.dataset.prompt;
            input.focus();
        };
    });
}
