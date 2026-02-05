(function(root, factory) {
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = factory();
    } else {
        root.Clipboard = factory();
    }
})(typeof window !== 'undefined' ? window : globalThis, function() {
    var STORAGE_KEY = 'clawos_clipboard_v1';

    function nowMs() {
        return Date.now ? Date.now() : new Date().getTime();
    }

    function safeJsonParse(text) {
        try {
            return JSON.parse(text);
        } catch (e) {
            return null;
        }
    }

    function normalizeOp(op) {
        return op === 'cut' || op === 'copy' ? op : null;
    }

    function normalizeState(raw) {
        if (!raw || typeof raw !== 'object') return null;
        var op = normalizeOp(raw.op);
        var path = typeof raw.path === 'string' ? raw.path : null;
        var name = typeof raw.name === 'string' ? raw.name : null;
        if (!op || !path || !name) return null;
        return {
            op: op,
            path: path,
            name: name,
            isDir: !!raw.isDir,
            ts: typeof raw.ts === 'number' ? raw.ts : nowMs()
        };
    }

    function createState(op, item) {
        var normalizedOp = normalizeOp(op);
        if (!normalizedOp) return null;
        if (!item || typeof item !== 'object') return null;
        var path = typeof item.path === 'string' ? item.path : null;
        var name = typeof item.name === 'string' ? item.name : null;
        if (!path || !name) return null;
        return {
            op: normalizedOp,
            path: path,
            name: name,
            isDir: !!item.isDir,
            ts: nowMs()
        };
    }

    function read(storage) {
        var s = storage;
        if (!s) {
            if (typeof window === 'undefined' || !window.localStorage) return null;
            s = window.localStorage;
        }
        try {
            var raw = s.getItem(STORAGE_KEY);
            if (!raw) return null;
            return normalizeState(safeJsonParse(raw));
        } catch (e) {
            return null;
        }
    }

    function write(storage, state) {
        var s = storage;
        if (!s) {
            if (typeof window === 'undefined' || !window.localStorage) return false;
            s = window.localStorage;
        }
        var normalized = normalizeState(state);
        if (!normalized) return false;
        try {
            s.setItem(STORAGE_KEY, JSON.stringify(normalized));
            return true;
        } catch (e) {
            return false;
        }
    }

    function clear(storage) {
        var s = storage;
        if (!s) {
            if (typeof window === 'undefined' || !window.localStorage) return false;
            s = window.localStorage;
        }
        try {
            s.removeItem(STORAGE_KEY);
            return true;
        } catch (e) {
            return false;
        }
    }

    function buildLabel(state) {
        var st = normalizeState(state);
        if (!st) return '';
        return '在此粘贴 ' + st.name;
    }

    function buildPasteRequest(state, targetPath) {
        var st = normalizeState(state);
        if (!st) return null;
        var target = typeof targetPath === 'string' ? targetPath : '';
        var endpoint = st.op === 'cut' ? '/api/batch/move' : '/api/batch/copy';
        return {
            endpoint: endpoint,
            payload: { paths: [st.path], target: target }
        };
    }

    function hasApiOkShape(data) {
        return !!(data && typeof data === 'object' && data.success === true);
    }

    function getApiMessage(data) {
        if (!data || typeof data !== 'object') return null;
        if (typeof data.message === 'string' && data.message) return data.message;
        if (data.error && typeof data.error.message === 'string' && data.error.message) return data.error.message;
        if (typeof data.error === 'string' && data.error) return data.error;
        return null;
    }

    function getCurrentBrowsePathFromDom() {
        if (typeof document === 'undefined') return '';
        var el = document.getElementById('currentBrowsePath');
        return el && typeof el.value === 'string' ? el.value : '';
    }

    function getUiElements() {
        if (typeof document === 'undefined') return null;
        var bar = document.getElementById('clipboardBar');
        var label = document.getElementById('clipboardLabel');
        var pasteBtn = document.getElementById('clipboardPasteBtn');
        var cancelBtn = document.getElementById('clipboardCancelBtn');
        if (!bar || !label || !pasteBtn || !cancelBtn) return null;
        return { bar: bar, label: label, pasteBtn: pasteBtn, cancelBtn: cancelBtn };
    }

    function setBarVisible(elements, visible) {
        if (!elements) return;
        elements.bar.style.display = visible ? 'flex' : 'none';
        elements.bar.setAttribute('aria-hidden', visible ? 'false' : 'true');
        if (!visible) elements.bar.removeAttribute('data-op');
    }

    function updateBottomOffset(elements) {
        if (!elements || typeof document === 'undefined') return;
        var batch = document.getElementById('batchActionBar');
        var batchVisible = batch && batch.style && batch.style.display !== 'none';
        elements.bar.style.bottom = batchVisible ? '84px' : '';
    }

    function render(elements, state) {
        var st = normalizeState(state);
        if (!elements) return;
        if (!st) {
            setBarVisible(elements, false);
            return;
        }
        elements.label.textContent = buildLabel(st);
        elements.bar.setAttribute('data-op', st.op);
        setBarVisible(elements, true);
        updateBottomOffset(elements);
    }

    function initUi() {
        var elements = getUiElements();
        if (!elements) return;
        elements.pasteBtn.addEventListener('click', function() {
            pasteHere();
        });
        elements.cancelBtn.addEventListener('click', function() {
            cancel();
        });
        elements.cancelBtn.addEventListener('keydown', function(e) {
            if (!e) return;
            if (e.key === 'Enter' || e.key === ' ') cancel();
        });
        if (typeof window !== 'undefined') {
            window.addEventListener('resize', function() {
                render(elements, read());
            });
        }
        render(elements, read());
    }

    function set(op, item) {
        var st = createState(op, item);
        if (!st) return false;
        write(null, st);
        render(getUiElements(), st);
        return true;
    }

    function cancel() {
        clear(null);
        render(getUiElements(), null);
    }

    function paste(state, targetPath, fetchFn) {
        var req = buildPasteRequest(state, targetPath);
        if (!req) return Promise.resolve({ ok: false, error: 'empty' });
        var f = fetchFn;
        if (!f) {
            if (typeof window === 'undefined' || !window.fetch) return Promise.resolve({ ok: false, error: 'no_fetch' });
            f = window.fetch.bind(window);
        }
        return f(req.endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(req.payload)
        })
            .then(function(r) { return r.json().catch(function() { return null; }); })
            .then(function(data) {
                if (hasApiOkShape(data)) return { ok: true, data: data };
                return { ok: false, data: data, error: getApiMessage(data) || 'failed' };
            })
            .catch(function(err) {
                return { ok: false, error: (err && err.message) || 'failed' };
            });
    }

    function pasteHere() {
        var st = read();
        if (!st) return;
        var target = getCurrentBrowsePathFromDom();
        paste(st, target)
            .then(function(res) {
                if (res && res.ok) {
                    cancel();
                    if (typeof window !== 'undefined' && typeof window.showToast === 'function') {
                        window.showToast('粘贴成功', 'success');
                    }
                    if (typeof window !== 'undefined' && typeof window.refreshFileList === 'function') {
                        window.refreshFileList();
                    }
                } else {
                    if (typeof window !== 'undefined' && typeof window.showToast === 'function') {
                        window.showToast((res && res.error) || '粘贴失败', 'error');
                    }
                }
            });
    }

    function autoInit() {
        if (typeof document === 'undefined') return;
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initUi);
        } else {
            initUi();
        }
    }

    autoInit();

    return {
        STORAGE_KEY: STORAGE_KEY,
        normalizeState: normalizeState,
        createState: createState,
        read: read,
        write: write,
        clear: clear,
        buildLabel: buildLabel,
        buildPasteRequest: buildPasteRequest,
        paste: paste,
        set: set,
        cancel: cancel,
        pasteHere: pasteHere,
        initUi: initUi
    };
});
