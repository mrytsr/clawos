const test = require('node:test');
const assert = require('node:assert/strict');

const TaskPoller = require('../static/js/task_poller.js');
const TaskActions = require('../static/js/task_actions.js');

function createTaskFetchSequence(statuses) {
    let idx = 0;
    return async (url, init) => {
        if (url === '/api/systemd/control') {
            assert.equal(init.method, 'POST');
            return { json: async () => ({ success: true, data: { taskId: 'task-1' } }) };
        }
        if (url.startsWith('/api/task/status')) {
            const status = statuses[Math.min(idx, statuses.length - 1)];
            idx += 1;
            return { json: async () => ({ status }) };
        }
        throw new Error('unexpected url: ' + url);
    };
}

test('success in 2 seconds shows listener and success toast', async () => {
    const ui = { visible: false, text: '', toasts: [] };
    const res = await TaskActions.controlSystemdService('clawos.service', 'restart', {
        fetchFn: createTaskFetchSequence(['pending', 'success']),
        headersFn: () => ({}),
        poller: TaskPoller,
        intervalMs: 10,
        timeoutMs: 80,
        show: (t) => { ui.visible = true; ui.text = t; },
        hide: () => { ui.visible = false; },
        toast: (msg, type) => { ui.toasts.push({ msg, type }); }
    });
    assert.equal(res.ok, true);
    assert.equal(ui.visible, false);
    assert.equal(ui.text, '正在监听任务状态…');
    assert.deepEqual(ui.toasts[0], { msg: '重启成功', type: 'success' });
});

test('immediate failed shows timeout toast', async () => {
    const ui = { visible: false, text: '', toasts: [] };
    const res = await TaskActions.controlSystemdService('clawos.service', 'restart', {
        fetchFn: createTaskFetchSequence(['failed']),
        headersFn: () => ({}),
        poller: TaskPoller,
        intervalMs: 10,
        timeoutMs: 80,
        show: (t) => { ui.visible = true; ui.text = t; },
        hide: () => { ui.visible = false; },
        toast: (msg, type) => { ui.toasts.push({ msg, type }); }
    });
    assert.equal(res.ok, false);
    assert.equal(ui.visible, false);
    assert.deepEqual(ui.toasts[0], { msg: '重启超时，请稍后重试', type: 'error' });
});

test('no success within 5 seconds shows timeout toast', async () => {
    const ui = { visible: false, text: '', toasts: [] };
    const res = await TaskActions.controlSystemdService('clawos.service', 'restart', {
        fetchFn: createTaskFetchSequence(['pending', 'pending', 'pending', 'pending', 'pending', 'pending']),
        headersFn: () => ({}),
        poller: TaskPoller,
        intervalMs: 10,
        timeoutMs: 50,
        show: (t) => { ui.visible = true; ui.text = t; },
        hide: () => { ui.visible = false; },
        toast: (msg, type) => { ui.toasts.push({ msg, type }); }
    });
    assert.equal(res.ok, false);
    assert.equal(ui.visible, false);
    assert.deepEqual(ui.toasts[0], { msg: '重启超时，请稍后重试', type: 'error' });
});
