const test = require('node:test');
const assert = require('node:assert/strict');

const TaskPoller = require('../static/js/task_poller.js');

test('success in 2 ticks resolves ok=true', async () => {
    let call = 0;
    const fetchFn = async () => {
        call += 1;
        if (call < 2) return { json: async () => ({ status: 'pending' }) };
        return { json: async () => ({ status: 'success' }) };
    };

    const handle = TaskPoller.start('t1', { intervalMs: 10, timeoutMs: 80, fetchFn });
    const res = await handle.promise;
    assert.equal(res.ok, true);
    assert.equal(res.status, 'success');
    assert.ok(call >= 2);
});

test('immediate failed resolves ok=false', async () => {
    const fetchFn = async () => ({ json: async () => ({ status: 'failed' }) });
    const handle = TaskPoller.start('t2', { intervalMs: 10, timeoutMs: 80, fetchFn });
    const res = await handle.promise;
    assert.equal(res.ok, false);
    assert.equal(res.status, 'failed');
});

test('timeout after 5 ticks resolves status=timeout', async () => {
    let call = 0;
    const fetchFn = async () => {
        call += 1;
        return { json: async () => ({ status: 'pending' }) };
    };
    const handle = TaskPoller.start('t3', { intervalMs: 10, timeoutMs: 50, fetchFn });
    const res = await handle.promise;
    assert.equal(res.ok, false);
    assert.equal(res.status, 'timeout');
    assert.ok(call >= 4);
});
