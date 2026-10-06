import test from 'node:test';
import assert from 'node:assert';
import { reducer, initialState } from '../store.js';
import { adaptEvent } from '../adapter.js';
import { selectCurrentStage } from '../selectors.js';

test('store initializes correctly', () => {
    const state = initialState();
    assert.deepStrictEqual(state.steps, []);
    assert.strictEqual(state.currentState, 'UNKNOWN');
});

test('reducer ignores duplicate seq', () => {
    let state = initialState();
    const event = { type: 'state', state: 'EXECUTING', seq: 1 };
    
    state = reducer(state, event);
    assert.strictEqual(state.currentState, 'EXECUTING');
    
    // Duplicate seq should be ignored
    const event2 = { type: 'state', state: 'DONE', seq: 1 };
    state = reducer(state, event2);
    assert.strictEqual(state.currentState, 'EXECUTING');
});

test('adapter adds seq and normalizes types', () => {
    const raw = { type: 'thought', content: 'test' };
    const adapted = adaptEvent(raw);
    assert.ok(adapted.seq > 0);
    assert.strictEqual(adapted.internalType, 'step_fragment');
});

test('selector maps state to stage correctly', () => {
    const state = { currentState: 'WAITING_APPROVAL' };
    assert.strictEqual(selectCurrentStage(state), 'Approve');
});
