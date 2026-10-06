export function reducer(state = initialState(), event) {
    if (!event || !event.type) return state;

    // Ignore duplicate seq if specified
    if (event.seq && state.seenSeqs.has(event.seq)) {
        return state;
    }

    const nextState = {
        ...state,
        seenSeqs: new Set(state.seenSeqs)
    };
    
    if (event.seq) {
        nextState.seenSeqs.add(event.seq);
    }

    switch (event.type) {
        case 'state':
            nextState.currentState = event.state;
            break;
        case 'task_started':
            nextState.task = event.task;
            nextState.runId = event.runId || nextState.runId;
            nextState.startTime = Date.now();
            nextState.status = 'running';
            break;
        case 'contract':
        case 'plan':
            nextState.contract = event.contract || event.data || event;
            if (nextState.contract) {
                if (nextState.contract.subgoals) nextState.subgoals = nextState.contract.subgoals;
                if (nextState.contract.success_points) nextState.successPoints = nextState.contract.success_points;
            }
            break;
        case 'plan_update':
            if (event.subgoals) {
                nextState.subgoals = event.subgoals;
            }
            if (event.success_points) {
                nextState.successPoints = event.success_points;
            }
            break;
        case 'budget_update':
        case 'budget':
            nextState.budget = { ...nextState.budget, ...event.data };
            break;
        case 'step_fragment':
            nextState.steps = [...nextState.steps, event];
            break;
        case 'guard':
            nextState.latestGuard = event;
            nextState.guardLogs = [...nextState.guardLogs, event];
            break;
        case 'assess':
            nextState.latestAssess = event;
            nextState.assessLogs = [...nextState.assessLogs, event];
            break;
        case 'run_completed':
            nextState.verdict = event.final_answer || event.status || 'Completed';
            nextState.status = event.status || 'completed';
            nextState.endTime = Date.now();
            if (event.status === 'failed' || (event.final_answer && event.final_answer.startsWith('VERIFIER REJECTION'))) {
                nextState.currentState = 'FAILED';
                nextState.status = 'failed';
            } else if (event.status === 'cancelled') {
                nextState.currentState = 'CANCELLED';
            } else if (event.status === 'completed') {
                nextState.currentState = 'DONE';
            }
            nextState.pendingApproval = null;
            break;
        case 'approval_required':
            nextState.pendingApproval = event.data || {
                tool: event.tool,
                args: event.args,
                preview: event.preview,
                risk: event.risk || 'HIGH',
                reason: event.reason || 'Mutating operation requires authorization.'
            };
            break;
        case 'approval_resolved':
            nextState.pendingApproval = null;
            break;
        case 'open_inspector':
            nextState.inspectorData = event.data;
            break;
        case 'close_inspector':
            nextState.inspectorData = null;
            break;
        default:
            nextState.rawEvents = [...nextState.rawEvents, event];
            break;
    }

    return nextState;
}

export function initialState() {
    return {
        seenSeqs: new Set(),
        currentState: 'UNKNOWN',
        status: 'idle',
        task: '',
        runId: '',
        startTime: null,
        endTime: null,
        contract: null,
        subgoals: [],
        successPoints: [],
        steps: [],
        guardLogs: [],
        assessLogs: [],
        latestGuard: null,
        latestAssess: null,
        rawEvents: [],
        budget: { steps: 0, maxSteps: 40, cost: '$0.00', duration: '0s' },
        verdict: null,
        pendingApproval: null,
        inspectorData: null
    };
}

