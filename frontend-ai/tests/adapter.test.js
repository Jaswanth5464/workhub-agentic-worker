import test from 'node:test';
import assert from 'node:assert';
import { adaptEvent, hashContent } from '../adapter.js';

test('adapter adds hash-based seq if missing', async () => {
    const raw = { type: 'thought', content: 'hello' };
    const adapted1 = await adaptEvent({ ...raw }, 0);
    const adapted2 = await adaptEvent({ ...raw }, 0);
    
    assert.ok(adapted1.seq.startsWith('hash-'));
    assert.strictEqual(adapted1.seq, adapted2.seq, "Same content and index should produce same hash");
});

test('adapter respects existing seq', async () => {
    const raw = { type: 'thought', content: 'hello', seq: 42 };
    const adapted = await adaptEvent(raw, 0);
    assert.strictEqual(adapted.seq, 42);
});
