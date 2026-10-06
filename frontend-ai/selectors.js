export function selectCurrentStage(state) {
    if (state.currentState === 'UNKNOWN') return 'Understand';
    const mapping = {
        'UNDERSTANDING': 'Understand',
        'CLARIFYING': 'Understand',
        'PLANNING': 'Plan',
        'EXECUTING': 'Execute',
        'RECOVERING': 'Execute',
        'WAITING_APPROVAL': 'Approve',
        'VERIFYING': 'Verify',
        'DONE': 'Report',
        'FAILED': 'Report',
        'NEEDS_USER': 'Report',
        'CANCELLED': 'Report'
    };
    return mapping[state.currentState] || 'Understand';
}

export function selectStepCounts(state) {
    return state.steps.length;
}

export function selectRawEvents(state) {
    return state.rawEvents;
}
