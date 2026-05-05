(function() {
    var editor = null;
    var currentConfigPayload = null;

    function apiData(resp) {
        if (resp && resp.success) return resp.data || {};
        return null;
    }

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function boolText(value) {
        return value ? 'true' : 'false';
    }

    function setEditorText(text) {
        if (editor) {
            editor.setValue(String(text || ''));
            return;
        }
        var el = document.getElementById('hermesConfigEditor');
        if (el) el.value = String(text || '');
    }

    function getEditorText() {
        if (editor) return editor.getValue();
        var el = document.getElementById('hermesConfigEditor');
        return el ? el.value : '';
    }

    function renderInstallState(state) {
        var box = document.getElementById('hermesInstallStateBox');
        if (!box) return;
        var installed = !!(state && state.installed);
        var shell = state && state.shell ? state.shell : 'none';
        var configExists = !!(state && state.config_exists);
        var repoExists = !!(state && state.repo_exists);
        box.innerHTML =
            '<div><strong>installed:</strong> ' + (installed ? 'yes' : 'no') + '</div>' +
            '<div><strong>shell:</strong> ' + escapeHtml(shell) + '</div>' +
            '<div><strong>config:</strong> ' + (configExists ? 'exists' : 'missing') + '</div>' +
            '<div><strong>repo:</strong> ' + (repoExists ? 'exists' : 'missing') + '</div>';

        var installBtn = document.getElementById('hermesInstallBtn');
        var uninstallBtn = document.getElementById('hermesUninstallBtn');
        if (installBtn) {
            installBtn.style.display = installed ? 'none' : 'inline-block';
            installBtn.disabled = shell === 'none';
            installBtn.title = shell === 'none' ? '未找到可用的 bash/WSL 环境' : '';
        }
        if (uninstallBtn) {
            uninstallBtn.style.display = installed ? 'inline-block' : 'none';
        }
    }

    function renderSummary(summary) {
        var box = document.getElementById('hermesSummaryBox');
        if (!box) return;
        if (!summary) {
            box.innerHTML = '<div style="color:#cf222e;">配置摘要不可用</div>';
            return;
        }
        box.innerHTML =
            '<div><strong>model.default:</strong> ' + escapeHtml(summary.model && summary.model.default) + '</div>' +
            '<div><strong>model.provider:</strong> ' + escapeHtml(summary.model && summary.model.provider) + '</div>' +
            '<div><strong>model.base_url:</strong> ' + escapeHtml(summary.model && summary.model.base_url) + '</div>' +
            '<div><strong>agent.max_turns:</strong> ' + escapeHtml(summary.agent && summary.agent.max_turns) + '</div>' +
            '<div><strong>agent.reasoning_effort:</strong> ' + escapeHtml(summary.agent && summary.agent.reasoning_effort) + '</div>' +
            '<div><strong>terminal.backend:</strong> ' + escapeHtml(summary.terminal && summary.terminal.backend) + '</div>' +
            '<div><strong>terminal.cwd:</strong> ' + escapeHtml(summary.terminal && summary.terminal.cwd) + '</div>' +
            '<div><strong>display.personality:</strong> ' + escapeHtml(summary.display && summary.display.personality) + '</div>' +
            '<div><strong>display.streaming:</strong> ' + boolText(summary.display && summary.display.streaming) + '</div>' +
            '<div><strong>browser.allow_private_urls:</strong> ' + boolText(summary.browser && summary.browser.allow_private_urls) + '</div>' +
            '<div><strong>approvals.mode:</strong> ' + escapeHtml(summary.approvals && summary.approvals.mode) + '</div>' +
            '<div><strong>toolsets:</strong> ' + escapeHtml(summary.counts && summary.counts.toolsets) + '</div>' +
            '<div><strong>custom_providers:</strong> ' + escapeHtml(summary.counts && summary.counts.custom_providers) + '</div>';
    }

    function setMetaText(text) {
        var el = document.getElementById('hermesEditorMeta');
        if (el) el.textContent = text || '';
    }

    function initEditor() {
        var textarea = document.getElementById('hermesConfigEditor');
        if (!textarea || typeof CodeMirror === 'undefined') return;
        editor = CodeMirror.fromTextArea(textarea, {
            mode: 'yaml',
            theme: 'dracula',
            lineNumbers: true,
            lineWrapping: false,
            indentUnit: 2,
            tabSize: 2,
        });
        editor.setSize('100%', '100%');
    }

    function loadHermesConfig() {
        var headers = typeof authHeaders === 'function' ? (authHeaders() || {}) : {};
        fetch('/api/hermes/config', { headers: headers })
            .then(function(r) { return r.json(); })
            .then(function(resp) {
                var payload = apiData(resp);
                if (!payload) {
                    throw new Error((resp && resp.error && resp.error.message) || '加载失败');
                }
                currentConfigPayload = payload;
                renderInstallState(payload.installState || {});
                renderSummary(payload.summary || null);
                setEditorText(payload.rawText || '');
                setMetaText((payload.exists ? '已加载' : '未找到配置文件') + ' · ' + (payload.configPath || '~/.hermes/config.yaml'));
                var hint = document.getElementById('hermesConfigPathHint');
                if (hint) hint.textContent = payload.configPath || '~/.hermes/config.yaml';
            })
            .catch(function(err) {
                renderSummary(null);
                setMetaText('');
                if (typeof showToast === 'function') showToast(err && err.message ? err.message : '加载失败', 'error');
            });
    }

    function saveHermesConfig() {
        var headers = typeof authHeaders === 'function' ? (authHeaders() || {}) : {};
        headers['Content-Type'] = 'application/json';
        if (typeof window.showTaskListener === 'function') {
            window.showTaskListener('正在保存 Hermes 配置...');
        }
        fetch('/api/hermes/config', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ rawText: getEditorText() })
        })
            .then(function(r) { return r.json(); })
            .then(function(resp) {
                if (typeof window.hideTaskListener === 'function') {
                    window.hideTaskListener();
                }
                var payload = apiData(resp);
                if (!payload) {
                    throw new Error((resp && resp.error && resp.error.message) || '保存失败');
                }
                renderSummary(payload.summary || null);
                if (typeof showToast === 'function') showToast('Hermes 配置已保存', 'success');
                loadHermesConfig();
            })
            .catch(function(err) {
                if (typeof window.hideTaskListener === 'function') {
                    window.hideTaskListener();
                }
                if (typeof showToast === 'function') showToast(err && err.message ? err.message : '保存失败', 'error');
            });
    }

    function pollTask(taskId, successMessage) {
        if (!taskId || !window.TaskPoller || typeof window.TaskPoller.start !== 'function') return;
        if (window.__activeTaskPoller && typeof window.__activeTaskPoller.cancel === 'function') {
            window.__activeTaskPoller.cancel();
        }
        window.__activeTaskPoller = window.TaskPoller.start(taskId, { intervalMs: 1000, timeoutMs: 15 * 60 * 1000 });
        window.__activeTaskPoller.promise.then(function(res) {
            window.__activeTaskPoller = null;
            if (typeof window.hideTaskListener === 'function') {
                window.hideTaskListener();
            }
            if (res && res.ok) {
                if (typeof showToast === 'function') showToast(successMessage, 'success');
                loadHermesConfig();
                return;
            }
            var msg = (((res || {}).payload || {}).message) || '任务执行失败';
            if (typeof showToast === 'function') showToast(msg, 'error');
            loadHermesConfig();
        });
    }

    function startHermesTask(action) {
        var headers = typeof authHeaders === 'function' ? (authHeaders() || {}) : {};
        headers['Content-Type'] = 'application/json';
        var url = action === 'install' ? '/api/hermes/install' : '/api/hermes/uninstall';
        var progressText = action === 'install' ? '正在安装 Hermes...' : '正在卸载 Hermes...';
        var successText = action === 'install' ? 'Hermes 安装完成' : 'Hermes 卸载完成';
        if (typeof window.showTaskListener === 'function') {
            window.showTaskListener(progressText);
        }
        fetch(url, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({})
        })
            .then(function(r) { return r.json(); })
            .then(function(resp) {
                var payload = apiData(resp);
                if (!payload || !payload.taskId) {
                    throw new Error((resp && resp.error && resp.error.message) || '任务创建失败');
                }
                pollTask(payload.taskId, successText);
            })
            .catch(function(err) {
                if (typeof window.hideTaskListener === 'function') {
                    window.hideTaskListener();
                }
                if (typeof showToast === 'function') showToast(err && err.message ? err.message : '任务创建失败', 'error');
            });
    }

    function bindActions() {
        var reloadBtn = document.getElementById('hermesReloadBtn');
        var saveBtn = document.getElementById('hermesSaveBtn');
        var installBtn = document.getElementById('hermesInstallBtn');
        var uninstallBtn = document.getElementById('hermesUninstallBtn');

        if (reloadBtn) reloadBtn.onclick = loadHermesConfig;
        if (saveBtn) saveBtn.onclick = saveHermesConfig;
        if (installBtn) installBtn.onclick = function() { startHermesTask('install'); };
        if (uninstallBtn) uninstallBtn.onclick = function() { startHermesTask('uninstall'); };
    }

    function boot() {
        initEditor();
        bindActions();
        loadHermesConfig();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }

    window.loadHermesConfig = loadHermesConfig;
})();
