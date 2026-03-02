(function(root, factory) {
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = factory();
    } else {
        root.TaskActions = factory();
    }
})(typeof window !== 'undefined' ? window : globalThis, function() {
    function getTaskId(payload) {
        if (!payload || typeof payload !== 'object') return null;
        if (typeof payload.taskId === 'string') return payload.taskId;
        if (payload.data && typeof payload.data.taskId === 'string') return payload.data.taskId;
        return null;
    }

    async function controlSystemdService(service, action, deps) {
        var d = deps || {};
        var fetchFn = d.fetchFn || (typeof window !== 'undefined' ? window.fetch && window.fetch.bind(window) : null);
        var headersFn = d.headersFn || (typeof window !== 'undefined' ? window.authHeaders : null);
        var poller = d.poller || (typeof window !== 'undefined' ? window.TaskPoller : null);
        var show = d.show || (typeof window !== 'undefined' ? window.showTaskListener : null);
        var hide = d.hide || (typeof window !== 'undefined' ? window.hideTaskListener : null);
        var toast = d.toast || (typeof window !== 'undefined' ? window.showToast : null);
        var setActive = d.setActive || (typeof window !== 'undefined' ? function(h) { window.__activeTaskPoller = h; } : null);
        var getActive = d.getActive || (typeof window !== 'undefined' ? function() { return window.__activeTaskPoller; } : function() { return null; });
        var intervalMs = typeof d.intervalMs === 'number' ? d.intervalMs : 1000;
        var timeoutMs = typeof d.timeoutMs === 'number' ? d.timeoutMs : 5000;

        var verb = action === 'start' ? '启动' : action === 'stop' ? '停止' : '重启';
        if (show) show('正在监听任务状态…');
        try {
            var existing = getActive && getActive();
            if (existing && typeof existing.cancel === 'function') existing.cancel();
            if (setActive) setActive(null);

            var resp = await fetchFn('/api/systemd/control', {
                method: 'POST',
                headers: Object.assign({ 'Content-Type': 'application/json' }, typeof headersFn === 'function' ? headersFn() : {}),
                body: JSON.stringify({ service: service, action: action })
            });
            var json = null;
            try { json = await resp.json(); } catch (e) { json = null; }
            var taskId = getTaskId(json && json.success ? json.data : json);
            if (!taskId || !poller || typeof poller.start !== 'function') {
                if (hide) hide();
                if (toast) toast('操作失败', 'error');
                return { ok: false, reason: 'no_task' };
            }

            var handle = poller.start(taskId, { intervalMs: intervalMs, timeoutMs: timeoutMs, fetchFn: fetchFn });
            if (setActive) setActive(handle);
            var result = await handle.promise;
            if (setActive) setActive(null);
            if (hide) hide();
            if (result && result.ok) {
                if (toast) toast(verb + '成功', 'success');
                return { ok: true, taskId: taskId };
            }
            if (toast) toast(verb + '超时，请稍后重试', 'error');
            return { ok: false, taskId: taskId };
        } catch (e) {
            if (setActive) setActive(null);
            if (hide) hide();
            if (toast) toast(verb + '超时，请稍后重试', 'error');
            return { ok: false, reason: 'exception' };
        }
    }

    return { controlSystemdService: controlSystemdService, _getTaskId: getTaskId };
});
