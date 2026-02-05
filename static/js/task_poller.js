(function(root, factory) {
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = factory();
    } else {
        root.TaskPoller = factory();
    }
})(typeof window !== 'undefined' ? window : globalThis, function() {
    function getStatusFromPayload(payload) {
        if (!payload || typeof payload !== 'object') return null;
        if (typeof payload.status === 'string') return payload.status;
        if (payload.data && typeof payload.data.status === 'string') return payload.data.status;
        return null;
    }

    function getTaskIdFromPayload(payload) {
        if (!payload || typeof payload !== 'object') return null;
        if (typeof payload.taskId === 'string') return payload.taskId;
        if (payload.data && typeof payload.data.taskId === 'string') return payload.data.taskId;
        return null;
    }

    function start(taskId, opts) {
        var options = opts || {};
        var intervalMs = typeof options.intervalMs === 'number' ? options.intervalMs : 1000;
        var timeoutMs = typeof options.timeoutMs === 'number' ? options.timeoutMs : 5000;
        var fetchFn = options.fetchFn;
        if (!fetchFn) {
            if (typeof window !== 'undefined' && window.fetch) fetchFn = window.fetch.bind(window);
        }
        var onUpdate = typeof options.onUpdate === 'function' ? options.onUpdate : null;

        var elapsedMs = 0;
        var done = false;
        var inFlight = false;
        var intervalId = null;

        function cancel() {
            if (done) return;
            done = true;
            if (intervalId) clearInterval(intervalId);
            intervalId = null;
        }

        var promise = new Promise(function(resolve) {
            intervalId = setInterval(async function() {
                if (done || inFlight) return;
                elapsedMs += intervalMs;
                inFlight = true;
                try {
                    var url = '/api/task/status?taskId=' + encodeURIComponent(taskId);
                    var resp = await fetchFn(url);
                    var json = null;
                    try { json = await resp.json(); } catch (e) { json = null; }
                    var status = getStatusFromPayload(json);
                    if (onUpdate) onUpdate({ taskId: taskId, status: status, payload: json });
                    if (status === 'success') {
                        cancel();
                        resolve({ ok: true, taskId: taskId, status: 'success', payload: json });
                        return;
                    }
                    if (status === 'failed') {
                        cancel();
                        resolve({ ok: false, taskId: taskId, status: 'failed', payload: json });
                        return;
                    }
                } catch (e) {
                    if (onUpdate) onUpdate({ taskId: taskId, status: null, error: e });
                } finally {
                    inFlight = false;
                }

                if (elapsedMs >= timeoutMs) {
                    cancel();
                    resolve({ ok: false, taskId: taskId, status: 'timeout' });
                }
            }, intervalMs);
        });

        return { promise: promise, cancel: cancel };
    }

    return {
        start: start,
        getStatusFromPayload: getStatusFromPayload,
        getTaskIdFromPayload: getTaskIdFromPayload
    };
});

