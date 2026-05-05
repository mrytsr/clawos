(function() {
    var editor = null;
    var currentConfigPayload = null;
    var currentHermesTab = 'config';

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

    function maskSecret(value) {
        var s = String(value == null ? '' : value).trim();
        if (!s) return '-';
        if (s.length <= 8) return '******';
        return s.slice(0, 4) + '...' + s.slice(-4);
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
        var installed = !!(state && state.installed);
        var shell = state && state.shell ? state.shell : 'none';
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

    function renderKeyValueRows(rows) {
        return rows.map(function(row, idx) {
            var border = idx < rows.length - 1 ? 'border-bottom:1px solid #eee;' : '';
            return '<div style="padding:10px 12px;' + border + 'display:flex;justify-content:space-between;align-items:center;gap:12px;">'
                + '<span style="color:#666;font-size:13px;">' + escapeHtml(row.label) + '</span>'
                + '<span style="font-size:13px;max-width:60%;text-align:right;word-break:break-word;">' + row.value + '</span>'
                + '</div>';
        }).join('');
    }

    function renderHermesConfigTab(payload) {
        var container = document.getElementById('hermesConfigContainer');
        if (!container) return;
        var summary = payload && payload.summary ? payload.summary : null;
        var state = payload && payload.installState ? payload.installState : {};
        if (!summary) {
            container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败</div>';
            return;
        }

        var html = '';

        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">安装状态</div>';
        html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
        html += renderKeyValueRows([
            { label: '状态', value: state.installed ? '<span style="color:#2da44e;">已安装</span>' : '<span style="color:#cf222e;">未安装</span>' },
            { label: '执行环境', value: escapeHtml(state.shell || '-') },
            { label: '配置文件', value: state.config_exists ? '存在' : '缺失' },
            { label: '仓库目录', value: state.repo_exists ? '存在' : '缺失' }
        ]);
        html += '</div></div>';

        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">概览</div>';
        html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
        html += renderKeyValueRows([
            { label: '配置路径', value: escapeHtml((payload && payload.configPath) || '~/.hermes/config.yaml') },
            { label: '默认模型', value: escapeHtml(summary.model && summary.model.default || '-') },
            { label: '模型提供商', value: escapeHtml(summary.model && summary.model.provider || '-') },
            { label: 'Base URL', value: escapeHtml(summary.model && summary.model.base_url || '-') },
            { label: '个性', value: escapeHtml(summary.display && summary.display.personality || '-') },
            { label: '审批模式', value: escapeHtml(summary.approvals && summary.approvals.mode || '-') },
            { label: 'Toolsets', value: escapeHtml(summary.counts && summary.counts.toolsets || 0) },
            { label: '自定义 Providers', value: escapeHtml(summary.counts && summary.counts.custom_providers || 0) }
        ]);
        html += '</div></div>';

        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">运行参数</div>';
        html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
        html += renderKeyValueRows([
            { label: 'max_turns', value: escapeHtml(summary.agent && summary.agent.max_turns || '-') },
            { label: 'reasoning_effort', value: escapeHtml(summary.agent && summary.agent.reasoning_effort || '-') },
            { label: 'tool_use_enforcement', value: escapeHtml(summary.agent && summary.agent.tool_use_enforcement || '-') },
            { label: 'terminal.backend', value: escapeHtml(summary.terminal && summary.terminal.backend || '-') },
            { label: 'terminal.cwd', value: escapeHtml(summary.terminal && summary.terminal.cwd || '-') },
            { label: 'browser.allow_private_urls', value: boolText(summary.browser && summary.browser.allow_private_urls) },
            { label: 'display.streaming', value: boolText(summary.display && summary.display.streaming) }
        ]);
        html += '</div></div>';

        container.innerHTML = html;
    }

    function renderHermesModelsTab(payload) {
        var container = document.getElementById('hermesModelsContainer');
        if (!container) return;
        var cfg = payload && payload.config ? payload.config : {};
        var summary = payload && payload.summary ? payload.summary : {};
        var customProviders = Array.isArray(cfg.custom_providers) ? cfg.custom_providers : [];

        var html = '';
        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">默认模型</div>';
        html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
        html += renderKeyValueRows([
            { label: 'model.default', value: escapeHtml(summary.model && summary.model.default || '-') },
            { label: 'model.provider', value: escapeHtml(summary.model && summary.model.provider || '-') },
            { label: 'model.base_url', value: escapeHtml(summary.model && summary.model.base_url || '-') }
        ]);
        html += '</div></div>';

        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">自定义 Providers</div>';
        html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
        if (!customProviders.length) {
            html += '<div style="padding:12px;color:#57606a;font-size:13px;">暂无自定义 Providers</div>';
        } else {
            customProviders.forEach(function(item, idx) {
                var border = idx < customProviders.length - 1 ? 'border-bottom:1px solid #eee;' : '';
                html += '<div style="padding:12px;' + border + '">';
                html += '<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">';
                html += '<div style="min-width:0;">';
                html += '<div style="font-weight:600;font-size:14px;word-break:break-all;">' + escapeHtml(item && item.name || '-') + '</div>';
                html += '<div style="font-size:12px;color:#57606a;margin-top:4px;word-break:break-all;">' + escapeHtml(item && item.base_url || '-') + '</div>';
                html += '</div>';
                html += '<div style="font-size:12px;color:#57606a;text-align:right;flex-shrink:0;">';
                html += '<div>model: ' + escapeHtml(item && item.model || '-') + '</div>';
                html += '<div>api_key: ' + escapeHtml(maskSecret(item && item.api_key || '')) + '</div>';
                html += '</div>';
                html += '</div>';
                html += '</div>';
            });
        }
        html += '</div></div>';

        container.innerHTML = html;
    }

    function renderHermesToolsetsTab(payload) {
        var container = document.getElementById('hermesToolsetsContainer');
        if (!container) return;
        var cfg = payload && payload.config ? payload.config : {};
        var toolsets = Array.isArray(cfg.toolsets) ? cfg.toolsets : [];
        var platformToolsets = cfg.platform_toolsets && typeof cfg.platform_toolsets === 'object' ? cfg.platform_toolsets : {};

        var html = '';
        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">默认 Toolsets</div>';
        html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;padding:12px;">';
        if (!toolsets.length) {
            html += '<div style="color:#57606a;font-size:13px;">暂无默认 Toolsets</div>';
        } else {
            html += toolsets.map(function(name) {
                return '<span style="display:inline-block;margin:4px 6px 0 0;padding:4px 10px;border-radius:999px;background:#f6f8fa;border:1px solid #d0d7de;font-size:12px;">' + escapeHtml(name) + '</span>';
            }).join('');
        }
        html += '</div></div>';

        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">平台 Toolsets</div>';
        html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
        var keys = Object.keys(platformToolsets);
        if (!keys.length) {
            html += '<div style="padding:12px;color:#57606a;font-size:13px;">暂无平台 Toolsets 配置</div>';
        } else {
            keys.forEach(function(key, idx) {
                var val = Array.isArray(platformToolsets[key]) ? platformToolsets[key] : [];
                var border = idx < keys.length - 1 ? 'border-bottom:1px solid #eee;' : '';
                html += '<div style="padding:12px;' + border + '">';
                html += '<div style="font-weight:600;font-size:14px;margin-bottom:6px;">' + escapeHtml(key) + '</div>';
                html += '<div style="font-size:12px;color:#57606a;">' + (val.length ? escapeHtml(val.join(', ')) : '未配置') + '</div>';
                html += '</div>';
            });
        }
        html += '</div></div>';

        container.innerHTML = html;
    }

    function renderHermesChatTab() {
        var container = document.getElementById('hermesChatContainer');
        if (!container) return;
        container.innerHTML = ''
            + '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">'
            + '<div style="padding:16px;">'
            + '<div style="font-weight:600;font-size:14px;margin-bottom:8px;">对话</div>'
            + '<div style="font-size:13px;color:#57606a;line-height:1.7;">'
            + '<div>当前页面先对齐 `OpenClaw` 的配置页风格。</div>'
            + '<div>Hermes 对话面板后续可继续接入独立聊天/状态能力。</div>'
            + '</div>'
            + '</div>'
            + '</div>';
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

    function renderAllPanels(payload) {
        renderHermesConfigTab(payload);
        renderHermesModelsTab(payload);
        renderHermesToolsetsTab(payload);
        renderHermesChatTab();
    }

    function loadHermesConfig() {
        var headers = typeof authHeaders === 'function' ? (authHeaders() || {}) : {};
        var configContainer = document.getElementById('hermesConfigContainer');
        var modelsContainer = document.getElementById('hermesModelsContainer');
        var toolsetsContainer = document.getElementById('hermesToolsetsContainer');
        var chatContainer = document.getElementById('hermesChatContainer');
        if (configContainer) configContainer.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
        if (modelsContainer) modelsContainer.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
        if (toolsetsContainer) toolsetsContainer.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
        if (chatContainer) chatContainer.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
        fetch('/api/hermes/config', { headers: headers })
            .then(function(r) { return r.json(); })
            .then(function(resp) {
                var payload = apiData(resp);
                if (!payload) {
                    throw new Error((resp && resp.error && resp.error.message) || '加载失败');
                }
                currentConfigPayload = payload;
                renderInstallState(payload.installState || {});
                renderAllPanels(payload);
                setEditorText(payload.rawText || '');
                setMetaText((payload.exists ? '已加载' : '未找到配置文件') + ' · ' + (payload.configPath || '~/.hermes/config.yaml'));
            })
            .catch(function(err) {
                renderAllPanels(null);
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
                currentConfigPayload = payload;
                renderAllPanels(payload);
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

    function switchHermesTab(tab) {
        currentHermesTab = tab || 'config';
        var panels = {
            config: document.getElementById('hermesConfigPanel'),
            models: document.getElementById('hermesModelsPanel'),
            toolsets: document.getElementById('hermesToolsetsPanel'),
            chat: document.getElementById('hermesChatPanel'),
            yaml: document.getElementById('hermesYamlPanel')
        };
        Object.keys(panels).forEach(function(key) {
            if (panels[key]) {
                panels[key].style.display = key === currentHermesTab ? (key === 'yaml' ? 'flex' : 'block') : 'none';
            }
        });
        var tabs = Array.prototype.slice.call(document.querySelectorAll('.bot-tab'));
        tabs.forEach(function(el) {
            var active = el && el.dataset && el.dataset.tab === currentHermesTab;
            el.classList.toggle('active', active);
            el.style.borderBottomColor = active ? '#0969da' : 'transparent';
            el.style.color = active ? '#24292f' : '#57606a';
            el.style.fontWeight = active ? '600' : '400';
        });
        if (editor && currentHermesTab === 'yaml') {
            setTimeout(function() { editor.refresh(); }, 0);
        }
    }

    function boot() {
        initEditor();
        bindActions();
        switchHermesTab('config');
        loadHermesConfig();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }

    window.loadHermesConfig = loadHermesConfig;
    window.switchHermesTab = switchHermesTab;
})();
