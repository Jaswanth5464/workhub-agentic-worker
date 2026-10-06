import { selectCurrentStage } from '../selectors.js';

export function renderPipelineStrip(root, state) {
    let el = root.querySelector('.pipeline-strip');
    if (!el) {
        el = document.createElement('div');
        el.className = 'pipeline-strip';
        root.appendChild(el);
    }
    
    const stages = [
        { name: 'Understand', icon: '🔍' },
        { name: 'Plan', icon: '📋' },
        { name: 'Execute', icon: '⚡' },
        { name: 'Approve', icon: '🛡️' },
        { name: 'Verify', icon: '✅' },
        { name: 'Report', icon: '📊' }
    ];
    
    let current = selectCurrentStage(state);
    if (state.pendingApproval) {
        current = 'Approve';
    }
    
    const currentIndex = stages.findIndex(s => s.name.toLowerCase() === (current || '').toLowerCase());
    
    el.innerHTML = stages.map((stage, idx) => {
        const isActive = stage.name.toLowerCase() === (current || '').toLowerCase();
        const isCompleted = currentIndex > idx || (state.status === 'completed' && !isActive);
        
        let pillClass = 'stage-pill';
        if (isActive) pillClass += ' active';
        else if (isCompleted) pillClass += ' completed';
        
        return `
            <div class="${pillClass}">
                <span>${isCompleted ? '✓' : stage.icon}</span>
                <span>${stage.name}</span>
            </div>
            ${idx < stages.length - 1 ? '<span class="stage-divider">→</span>' : ''}
        `;
    }).join('');
}
