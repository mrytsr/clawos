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

    function apiHeaders(json) {
        var headers = typeof authHeaders === 'function' ? (authHeaders() || {}) : {};
        if (json) headers['Content-Type'] = 'application/json';
        return headers;
    }

    function apiFetch(url, options) {
        return fetch(url, options || {})
            .then(function(r) { return r.json(); })
            .then(function(resp) {
                var payload = apiData(resp);
                if (!payload) {
                    throw new Error((resp && resp.error && resp.error.message) || '请求失败');
                }
                return payload;
            });
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
        var modelsPayload = payload && payload.models ? payload.models : null;
        var defaultModel = modelsPayload && modelsPayload.defaultModel ? modelsPayload.defaultModel : { default: '', provider: '', base_url: '', api_key_masked: '' };
        var customProviders = modelsPayload && Array.isArray(modelsPayload.providers) ? modelsPayload.providers : [];

        var html = '';
        html += '<div style="margin-bottom:16px;">';
        html += '<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:8px;padding-left:4px;">';
        html += '<div style="font-size:13px;color:#666;">默认模型</div>';
        html += '<button onclick="openHermesDefaultModelDialog()" style="background:#0969da;border:none;border-radius:6px;color:#fff;padding:6px 10px;cursor:pointer;font-size:12px;">编辑当前模型</button>';
        html += '</div>';
        html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
        html += renderKeyValueRows([
            { label: 'model.default', value: escapeHtml(defaultModel.default || '-') },
            { label: 'model.provider', value: escapeHtml(defaultModel.provider || '-') },
            { label: 'model.base_url', value: escapeHtml(defaultModel.base_url || '-') },
            { label: 'model.api_key', value: escapeHtml(defaultModel.api_key_masked || '-') }
        ]);
        html += '</div></div>';

        html += '<div style="margin-bottom:16px;">';
        html += '<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:8px;padding-left:4px;">';
        html += '<div style="font-size:13px;color:#666;">自定义 Providers</div>';
        html += '<button onclick="openHermesAddProviderDialog()" style="background:#2da44e;border:none;border-radius:6px;color:#fff;padding:6px 10px;cursor:pointer;font-size:12px;">+ 添加</button>';
        html += '</div>';
        html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
        if (!customProviders.length) {
            html += '<div style="padding:12px;color:#57606a;font-size:13px;">暂无自定义 Providers</div>';
        } else {
            customProviders.forEach(function(item, idx) {
                var border = idx < customProviders.length - 1 ? 'border-bottom:1px solid #eee;' : '';
                var isActive = (defaultModel.default || '') === (item && item.model || '') && (defaultModel.base_url || '') === (item && item.base_url || '');
                html += '<div style="padding:12px;' + border + '">';
                html += '<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">';
                html += '<div style="min-width:0;">';
                html += '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">';
                html += '<div style="font-weight:600;font-size:14px;word-break:break-all;">' + escapeHtml(item && item.name || '-') + '</div>';
                if (isActive) {
                    html += '<span style="font-size:11px;padding:1px 6px;border-radius:999px;background:#dafbe1;color:#1a7f37;">当前</span>';
                }
                html += '</div>';
                html += '<div style="font-size:12px;color:#57606a;margin-top:4px;word-break:break-all;">' + escapeHtml(item && item.base_url || '-') + '</div>';
                html += '<div style="font-size:12px;color:#57606a;margin-top:4px;">model: ' + escapeHtml(item && item.model || '-') + '</div>';
                html += '<div style="font-size:12px;color:#57606a;margin-top:2px;">api_key: ' + escapeHtml(item && item.api_key_masked || '-') + '</div>';
                html += '</div>';
                html += '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:flex-end;flex-shrink:0;">';
                if (isActive) {
                    html += '<span style="font-size:12px;padding:6px 10px;border-radius:6px;background:#dafbe1;color:#1a7f37;">当前</span>';
                } else {
                    html += '<button onclick="setHermesProviderAsDefault(' + JSON.stringify(item && item.name || '') + ')" style="background:#2da44e;border:none;border-radius:6px;color:#fff;padding:6px 10px;cursor:pointer;font-size:12px;">设为当前</button>';
                }
                html += '<button onclick="openHermesEditProviderDialog(' + JSON.stringify(item && item.name || '') + ')" style="background:#0969da;border:none;border-radius:6px;color:#fff;padding:6px 10px;cursor:pointer;font-size:12px;">编辑</button>';
                html += '<button onclick="removeHermesProvider(' + JSON.stringify(item && item.name || '') + ')" style="background:#cf222e;border:none;border-radius:6px;color:#fff;padding:6px 10px;cursor:pointer;font-size:12px;">删除</button>';
                html += '</div>';
                html += '</div>';
                html += '</div>';
            });
        }
        html += '</div></div>';

        container.innerHTML = html;
    }

    function refreshHermesModelsFromApi() {
        return apiFetch('/api/hermes/models', { headers: apiHeaders(false) })
            .then(function(modelsPayload) {
                currentConfigPayload = currentConfigPayload || {};
                currentConfigPayload.models = modelsPayload;
                renderHermesModelsTab(currentConfigPayload);
                return modelsPayload;
            });
    }

    function showDialogError(dialogId, msg) {
        var el = document.getElementById(dialogId);
        if (!el) return;
        el.style.display = msg ? 'block' : 'none';
        el.textContent = msg || '';
    }

    function createHermesDialog(title, bodyHtml, submitLabel, onSubmit) {
        var overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.42);z-index:26000;display:flex;align-items:center;justify-content:center;padding:16px;';
        var errorId = 'hermesDialogError_' + String(Date.now()) + '_' + Math.floor(Math.random() * 1000);
        var panel = document.createElement('div');
        panel.style.cssText = 'background:#fff;border-radius:12px;width:min(720px,100%);max-height:90vh;overflow:auto;box-shadow:0 18px 44px rgba(0,0,0,0.25);';
        panel.innerHTML =
            '<div style="padding:14px 18px;border-bottom:1px solid #eaeef2;display:flex;justify-content:space-between;align-items:center;">'
            + '<div style="font-size:16px;font-weight:600;">' + escapeHtml(title) + '</div>'
            + '<button data-role="close" style="border:none;background:none;font-size:24px;line-height:1;cursor:pointer;color:#57606a;">×</button>'
            + '</div>'
            + '<div style="padding:16px 18px;">' + bodyHtml + '</div>'
            + '<div id="' + errorId + '" style="display:none;color:#cf222e;font-size:13px;padding:0 18px 10px;"></div>'
            + '<div style="padding:12px 18px;border-top:1px solid #eaeef2;display:flex;gap:8px;justify-content:flex-end;">'
            + '<button data-role="cancel" style="padding:8px 14px;border:1px solid #d0d7de;border-radius:8px;background:#fff;cursor:pointer;">取消</button>'
            + '<button data-role="submit" style="padding:8px 14px;border:none;border-radius:8px;background:#0969da;color:#fff;cursor:pointer;">' + escapeHtml(submitLabel || '保存') + '</button>'
            + '</div>';
        overlay.appendChild(panel);
        document.body.appendChild(overlay);
        function closeDialog() { overlay.remove(); }
        overlay.addEventListener('click', function(ev) { if (ev.target === overlay) closeDialog(); });
        var closeBtn = panel.querySelector('[data-role="close"]');
        var cancelBtn = panel.querySelector('[data-role="cancel"]');
        var submitBtn = panel.querySelector('[data-role="submit"]');
        if (closeBtn) closeBtn.onclick = closeDialog;
        if (cancelBtn) cancelBtn.onclick = closeDialog;
        if (submitBtn) {
            submitBtn.onclick = function() {
                showDialogError(errorId, '');
                onSubmit(function(msg) { showDialogError(errorId, msg); }, closeDialog);
            };
        }
    }

    function getHermesModelsPayload() {
        return currentConfigPayload && currentConfigPayload.models ? currentConfigPayload.models : { defaultModel: {}, providers: [] };
    }

    function openHermesDefaultModelDialog() {
        var current = getHermesModelsPayload().defaultModel || {};
        createHermesDialog(
            '编辑当前模型',
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
                + '<div><div style="font-size:12px;color:#57606a;margin-bottom:6px;">默认模型</div><input id="hermesDefaultModelInput" style="width:100%;padding:8px 10px;border:1px solid #d0d7de;border-radius:8px;box-sizing:border-box;" value="' + escapeHtml(current.default || '') + '"></div>'
                + '<div><div style="font-size:12px;color:#57606a;margin-bottom:6px;">Provider</div><input id="hermesDefaultProviderInput" style="width:100%;padding:8px 10px;border:1px solid #d0d7de;border-radius:8px;box-sizing:border-box;" value="' + escapeHtml(current.provider || '') + '"></div>'
                + '<div style="grid-column:1 / span 2;"><div style="font-size:12px;color:#57606a;margin-bottom:6px;">Base URL</div><input id="hermesDefaultBaseUrlInput" style="width:100%;padding:8px 10px;border:1px solid #d0d7de;border-radius:8px;box-sizing:border-box;" value="' + escapeHtml(current.base_url || '') + '"></div>'
                + '<div style="grid-column:1 / span 2;"><div style="font-size:12px;color:#57606a;margin-bottom:6px;">API Key' + (current.api_key_masked ? '（当前已设置）' : '') + '</div><input id="hermesDefaultApiKeyInput" type="password" placeholder="留空则保留现有值" style="width:100%;padding:8px 10px;border:1px solid #d0d7de;border-radius:8px;box-sizing:border-box;"></div>'
                + '</div>',
            '保存',
            function(setError, closeDialog) {
                var defaultEl = document.getElementById('hermesDefaultModelInput');
                var providerEl = document.getElementById('hermesDefaultProviderInput');
                var baseUrlEl = document.getElementById('hermesDefaultBaseUrlInput');
                var apiKeyEl = document.getElementById('hermesDefaultApiKeyInput');
                var payload = {
                    default: defaultEl ? defaultEl.value.trim() : '',
                    provider: providerEl ? providerEl.value.trim() : '',
                    base_url: baseUrlEl ? baseUrlEl.value.trim() : '',
                    api_key: apiKeyEl ? apiKeyEl.value.trim() : ''
                };
                if (!payload.default) {
                    setError('请输入默认模型');
                    return;
                }
                apiFetch('/api/hermes/models/save_default', {
                    method: 'POST',
                    headers: apiHeaders(true),
                    body: JSON.stringify(payload)
                }).then(function(modelsPayload) {
                    currentConfigPayload = currentConfigPayload || {};
                    currentConfigPayload.models = modelsPayload;
                    closeDialog();
                    loadHermesConfig();
                    if (typeof showToast === 'function') showToast('默认模型已保存', 'success');
                }).catch(function(err) {
                    setError(err && err.message ? err.message : '保存失败');
                });
            }
        );
    }

    function openHermesProviderDialog(mode, current) {
        var isEdit = mode === 'edit';
        var item = current || {};
        createHermesDialog(
            isEdit ? '编辑 Provider' : '添加 Provider',
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
                + '<div><div style="font-size:12px;color:#57606a;margin-bottom:6px;">名称</div><input id="hermesProviderNameInput" style="width:100%;padding:8px 10px;border:1px solid #d0d7de;border-radius:8px;box-sizing:border-box;" value="' + escapeHtml(item.name || '') + '"></div>'
                + '<div><div style="font-size:12px;color:#57606a;margin-bottom:6px;">模型</div><input id="hermesProviderModelInput" style="width:100%;padding:8px 10px;border:1px solid #d0d7de;border-radius:8px;box-sizing:border-box;" value="' + escapeHtml(item.model || '') + '"></div>'
                + '<div style="grid-column:1 / span 2;"><div style="font-size:12px;color:#57606a;margin-bottom:6px;">Base URL</div><input id="hermesProviderBaseUrlInput" style="width:100%;padding:8px 10px;border:1px solid #d0d7de;border-radius:8px;box-sizing:border-box;" value="' + escapeHtml(item.base_url || '') + '"></div>'
                + '<div style="grid-column:1 / span 2;"><div style="font-size:12px;color:#57606a;margin-bottom:6px;">API Key' + (isEdit && item.api_key_masked ? '（当前已设置）' : '') + '</div><input id="hermesProviderApiKeyInput" type="password" placeholder="' + (isEdit ? '留空则保留现有值' : 'sk-xxxx') + '" style="width:100%;padding:8px 10px;border:1px solid #d0d7de;border-radius:8px;box-sizing:border-box;"></div>'
                + '</div>',
            isEdit ? '保存' : '添加',
            function(setError, closeDialog) {
                var nameEl = document.getElementById('hermesProviderNameInput');
                var modelEl = document.getElementById('hermesProviderModelInput');
                var baseUrlEl = document.getElementById('hermesProviderBaseUrlInput');
                var apiKeyEl = document.getElementById('hermesProviderApiKeyInput');
                var payload = {
                    name: nameEl ? nameEl.value.trim() : '',
                    model: modelEl ? modelEl.value.trim() : '',
                    base_url: baseUrlEl ? baseUrlEl.value.trim() : '',
                    api_key: apiKeyEl ? apiKeyEl.value.trim() : ''
                };
                if (!payload.name) {
                    setError('请输入 provider 名称');
                    return;
                }
                if (!payload.model) {
                    setError('请输入模型名称');
                    return;
                }
                var url = '/api/hermes/models/add';
                if (isEdit) {
                    url = '/api/hermes/models/update';
                    payload.originalName = item.name || '';
                }
                apiFetch(url, {
                    method: 'POST',
                    headers: apiHeaders(true),
                    body: JSON.stringify(payload)
                }).then(function(modelsPayload) {
                    currentConfigPayload = currentConfigPayload || {};
                    currentConfigPayload.models = modelsPayload;
                    closeDialog();
                    loadHermesConfig();
                    if (typeof showToast === 'function') showToast(isEdit ? 'Provider 已保存' : 'Provider 已添加', 'success');
                }).catch(function(err) {
                    setError(err && err.message ? err.message : (isEdit ? '保存失败' : '添加失败'));
                });
            }
        );
    }

    function openHermesAddProviderDialog() {
        openHermesProviderDialog('add', null);
    }

    function openHermesEditProviderDialog(name) {
        var providers = getHermesModelsPayload().providers || [];
        var current = providers.find(function(item) { return (item && item.name || '') === (name || ''); });
        if (!current) {
            if (typeof showToast === 'function') showToast('Provider 不存在', 'error');
            return;
        }
        openHermesProviderDialog('edit', current);
    }

    function setHermesProviderAsDefault(name) {
        var providerName = String(name || '').trim();
        if (!providerName) return;
        apiFetch('/api/hermes/models/set_default', {
            method: 'POST',
            headers: apiHeaders(true),
            body: JSON.stringify({ name: providerName })
        }).then(function(modelsPayload) {
            currentConfigPayload = currentConfigPayload || {};
            currentConfigPayload.models = modelsPayload;
            loadHermesConfig();
            if (typeof showToast === 'function') showToast('已切换当前模型', 'success');
        }).catch(function(err) {
            if (typeof showToast === 'function') showToast(err && err.message ? err.message : '切换失败', 'error');
        });
    }

    function removeHermesProvider(name) {
        var providerName = String(name || '').trim();
        if (!providerName) return;
        if (!window.confirm('确定删除 provider ' + providerName + ' 吗？')) return;
        apiFetch('/api/hermes/models/remove', {
            method: 'POST',
            headers: apiHeaders(true),
            body: JSON.stringify({ name: providerName })
        }).then(function(modelsPayload) {
            currentConfigPayload = currentConfigPayload || {};
            currentConfigPayload.models = modelsPayload;
            loadHermesConfig();
            if (typeof showToast === 'function') showToast('Provider 已删除', 'success');
        }).catch(function(err) {
            if (typeof showToast === 'function') showToast(err && err.message ? err.message : '删除失败', 'error');
        });
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
                payload.models = {
                    defaultModel: {
                        default: payload.summary && payload.summary.model ? payload.summary.model.default : '',
                        provider: payload.summary && payload.summary.model ? payload.summary.model.provider : '',
                        base_url: payload.summary && payload.summary.model ? payload.summary.model.base_url : '',
                        api_key_masked: payload.config && payload.config.model && payload.config.model.api_key ? '******' : ''
                    },
                    providers: Array.isArray(payload.config && payload.config.custom_providers) ? payload.config.custom_providers.map(function(item) {
                        return {
                            name: item && item.name || '',
                            model: item && item.model || '',
                            base_url: item && item.base_url || '',
                            api_key_masked: item && item.api_key ? '******' : ''
                        };
                    }) : []
                };
                renderInstallState(payload.installState || {});
                renderAllPanels(payload);
                setEditorText(payload.rawText || '');
                setMetaText((payload.exists ? '已加载' : '未找到配置文件') + ' · ' + (payload.configPath || '~/.hermes/config.yaml'));
                refreshHermesModelsFromApi().catch(function() {});
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
    window.openHermesAddProviderDialog = openHermesAddProviderDialog;
    window.openHermesEditProviderDialog = openHermesEditProviderDialog;
    window.setHermesProviderAsDefault = setHermesProviderAsDefault;
    window.removeHermesProvider = removeHermesProvider;
    window.openHermesDefaultModelDialog = openHermesDefaultModelDialog;
})();
