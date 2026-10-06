export async function hashContent(obj) {
    const str = JSON.stringify(obj);
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = (hash << 5) - hash + str.charCodeAt(i);
        hash |= 0; 
    }
    return hash.toString(16);
}

export async function adaptEvent(event, index = 0) {
    if (!event) return null;
    
    // Add seq if missing using a content hash to drop duplicates
    if (typeof event.seq === 'undefined') {
        const hash = await hashContent({ type: event.type, content: event.content, step: index });
        event.seq = `hash-${hash}`;
    }

    switch (event.type) {
        case 'thought':
        case 'action':
        case 'observation':
            return {
                ...event,
                internalType: event.type,
                type: 'step_fragment'
            };
        case 'phase_change':
            return { ...event, type: 'state', state: event.phase || event.state };
        case 'contract':
        case 'plan':
        case 'guard':
        case 'assess':
        case 'approval_required':
        case 'run_completed':
        case 'budget_update':
        case 'budget':
            return event;
        default:
            return event;
    }
}
