window.loadGitList = function(specificRepoPath) {
    const container = document.getElementById('gitListContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:20px;color:#666;">🔄 加载中...</div>';
    
    // 如果指定了路径，直接获取该仓库的信息
    if (specificRepoPath) {
        fetch('/api/git/repo-status?path=' + encodeURIComponent(specificRepoPath), { headers: authHeaders() })
            .then(r => r.json())
            .then(data => {
                const payload = apiData(data);
                if (container) {
                    if (payload && payload.is_repo) {
                        const repo = payload;
                        const branch = repo.branch || 'unknown';
                        const commit = repo.commit || '';
                        const repoStatus = repo.status || {};
                        const hasChanges = repoStatus.has_changes || false;
                        
                        // 状态显示
                        let statusText = hasChanges ? '✗ Dirty' : '✓ Clean';
                        let statusClass = hasChanges ? 'dirty' : 'clean';
                        let changeInfo = '';
                        if (hasChanges) {
                            const changes = [];
                            if (repoStatus.untracked > 0) changes.push('[+' + repoStatus.untracked + ']');
                            if (repoStatus.modified > 0) changes.push('[~' + repoStatus.modified + ']');
                            if (repoStatus.deleted > 0) changes.push('[-' + repoStatus.deleted + ']');
                            if (changes.length > 0) changeInfo = ' ' + changes.join(' ');
                        }
                        
                        // 日志列表
                        const logs = repo.logs || [];
                        let logsHtml = '';
                        if (logs.length === 0) {
                            logsHtml = '<div style="padding:16px;text-align:center;color:#666;">暂无提交记录</div>';
                        } else {
                            logsHtml = logs.map(function(log) {
                                const time = escapeHtml(log.committed_at || '');
                                const subject = escapeHtml(log.subject || '');
                                const shortHash = escapeHtml(String(log.hash || '').slice(0, 7));
                                const hash = escapeHtml(log.hash || '');
                                const repoPath = escapeHtml(specificRepoPath);
                                return '<div class="git-item" data-hash="' + hash + '" onclick="loadGitCommitDetail(\'' + repoPath + '\', \'' + hash + '\')"><div class="git-meta"><span class="git-time">' + time + '</span><span class="git-hash" data-hash="' + hash + '" data-repo="' + repoPath + '">' + shortHash + '</span><span style="background:#ddf4ff;color:#0969da;padding:1px 6px;border-radius:999px;font-size:10px;">' + escapeHtml(branch) + '</span></div><div class="git-subject" title="' + subject + '">' + (subject || '-') + '</div></div>';
                            }).join('');
                        }
                        
                        // 头部信息
                        const headerHtml = '<div style="padding:12px 16px;background:#f6f8fa;border-bottom:1px solid #d0d7de;border-radius:8px 8px 0 0;"><div style="font-size:14px;font-weight:600;color:#24292f;margin-bottom:8px;">📦 ' + escapeHtml(repo.name) + '</div><div style="font-size:12px;color:#57606a;">分支: <span style="background:#ddf4ff;color:#0969da;padding:1px 6px;border-radius:999px;font-size:10px;">' + escapeHtml(branch) + '</span> <span style="font-family:ui-monospace;color:#57606a;">@' + escapeHtml(commit) + '</span></div><div style="font-size:12px;color:#57606a;margin-top:4px;word-break:break-all;">路径: ' + escapeHtml(repo.path) + '</div><div style="font-size:12px;color:' + (hasChanges ? '#cf222e' : '#2da44e') + ';margin-top:4px;">' + statusText + changeInfo + '</div></div>';
                        
                        container.innerHTML = '<div class="git-shell">' + headerHtml + '<div class="git-list" id="gitLogList">' + logsHtml + '</div></div>';
                    } else {
                        container.innerHTML = '<div style="padding:16px;text-align:center;color:#cf222e;">此目录不是Git仓库</div>';
                    }
                }
            })
            .catch(function() {
                if (container) container.innerHTML = '<div style="padding:16px;text-align:center;color:#cf222e;">加载失败</div>';
            });
        return;
    }
    
    // 原版：使用下拉选择多个仓库
    fetch('/api/git/list', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload && payload.repos) {
                const container = document.getElementById('gitListContainer');
                if (container) {
                    window.__gitRepos = payload.repos || [];
                    const css = '<style>.git-shell { display:flex; flex-direction:column; gap:10px; }.git-top { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }.git-select { padding:8px 12px; border:1px solid #d0d7de; border-radius:8px; background:#fff; font-size:14px; flex:1; }.git-list { max-height: calc(70vh - 100px); overflow:auto; }.git-item { padding:10px 12px; border-bottom:1px solid #eee; cursor:pointer; display:flex; flex-direction:column; gap:4px; }.git-item:hover { background:#f6f8fa; }.git-item.active { background:#ddf4ff; }.git-meta { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }.git-time { font-size:12px; color:#0969da; font-family: ui-monospace, monospace; }.git-hash { font-size:11px; color:#57606a; font-family: ui-monospace, monospace; cursor:pointer; }.git-hash:hover { color:#0969da; text-decoration:underline; }.git-subject { font-size:13px; color:#24292f; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }</style>';
                    const html = css + '<div class="git-shell"><div class="git-top"><span style="font-size:12px;color:#57606a;">仓库</span><select id="gitRepoSelect" class="git-select"></select></div><div class="git-list" id="gitCommitList"></div></div>';
                    container.innerHTML = html;

                    const repos = window.__gitRepos || [];
                    const select = document.getElementById('gitRepoSelect');
                    const listEl = document.getElementById('gitCommitList');

                    function renderRepo(repo) {
                        if (!repo) return;
                        state.repoId = repo.id;
                        const branch = repo.status ? repo.status.branch : '-';
                        select.value = String(repo.id);

                        const logs = Array.isArray(repo.logs) ? repo.logs.slice(0, 50) : [];
                        if (logs.length === 0) {
                            listEl.innerHTML = '<div style="padding:16px;text-align:center;color:#666;">暂无提交记录</div>';
                            return;
                        }
                        listEl.innerHTML = logs.map(function(log) {
                            const time = escapeHtml(log.committed_at || '');
                            const subject = escapeHtml(log.subject || '');
                            const shortHash = escapeHtml(String(log.hash || '').slice(0, 7));
                            const hash = escapeHtml(log.hash || '');
                            return '<div class="git-item" data-hash="' + hash + '" onclick="loadGitCommitDetail(\'' + repo.id + '\', \'' + hash + '\')"><div class="git-meta"><span class="git-time">' + time + '</span><span class="git-hash" data-hash="' + hash + '" data-repo="' + repo.id + '">' + shortHash + '</span><span style="background:#ddf4ff;color:#0969da;padding:1px 6px;border-radius:999px;font-size:10px;">' + escapeHtml(branch) + '</span></div><div class="git-subject" title="' + subject + '">' + (subject || '-') + '</div></div>';
                        }).join('');
                    }

                    repos.forEach(function(r) {
                        const opt = document.createElement('option');
                        opt.value = String(r.id);
                        opt.textContent = r.name + ' (' + (r.status && r.status.branch ? r.status.branch : '-') + ')';
                        select.appendChild(opt);
                    });

                    select.addEventListener('change', function() {
                        const rid = this.value;
                        const repo = repos.find(function(r) { return String(r.id) === String(rid); });
                        renderRepo(repo);
                    });

                    if (repos.length > 0) renderRepo(repos[0]);
                }
            }
        });
};
window.closeGitModal = function() { Drawer.close('gitModal'); };
window.openGitModal = function() { Drawer.open('gitModal'); loadGitList(); };
window.openProcessModal = function() { Drawer.open('processModal'); loadProcessList(); };
window.openSystemPackageModal = function() { Drawer.open('systemPackageModal'); loadSystemPackageList(); };
window.openPipModal = function() { Drawer.open('pipModal'); loadPipList(); };
window.openNpmModal = function() { Drawer.open('npmModal'); loadNpmList(); };
window.openDockerModal = function() { Drawer.open('dockerModal'); loadDockerTabs(); };
window.openSystemdModal = function() { Drawer.open('systemdModal'); loadSystemdList(); };
window.openDiskModal = function() { Drawer.open('diskModal'); loadDiskList(); };
window.openNetworkModal = function() { Drawer.open('networkModal'); loadNetworkList(); };

// GPU显卡信息
window.loadGpuInfo = function() {
    const container = document.getElementById('gpuInfoContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/gpu/info', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload && container) {
                const p = payload.parsed || {};
                const gpuName = p.name || 'Unknown GPU';
                const memoryUsed = p.memory_used || 0;
                const memoryTotal = p.memory_total || 1;
                const memoryPercent = p.memory_percent || 0;
                const temp = p.temperature || 0;
                const powerUsed = p.power_used || 0;
                const powerTotal = p.power_total || 260;
                const util = p.utilization || 0;
                const driver = p.driver || 'Unknown';
                const cuda = p.cuda || 'Unknown';
                
                const memoryBar = renderProgressBar(memoryUsed, memoryTotal, 'MiB');
                const powerBar = renderProgressBar(powerUsed, powerTotal, 'W');
                const utilBar = renderProgressBar(util, 100, '%');
                
                container.innerHTML = '<div style="background:#f6f8fa;padding:12px 16px;border-radius:8px;margin-bottom:12px;"><div style="font-size:18px;font-weight:600;margin-bottom:4px;">' + escapeHtml(gpuName) + '</div><div style="font-size:12px;color:#666;">驱动: ' + escapeHtml(driver) + ' | CUDA: ' + escapeHtml(cuda) + '</div></div><div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:16px;"><div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center;"><div style="font-size:24px;font-weight:600;color:' + (temp > 70 ? '#cf222e' : '#24292f') + '">' + temp + '°C</div><div style="font-size:12px;color:#666;margin-top:4px;">温度</div></div><div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center;"><div style="font-size:24px;font-weight:600;color:#24292f">' + util + '%</div><div style="font-size:12px;color:#666;margin-top:4px;">利用率</div></div></div><div style="margin-bottom:12px;"><div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;"><span>显存 ' + memoryUsed + ' / ' + memoryTotal + ' MiB</span><span>' + memoryPercent + '%</span></div><div style="height:8px;background:#e1e4e8;border-radius:4px;overflow:hidden;">' + memoryBar + '</div></div><div style="margin-bottom:12px;"><div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;"><span>功耗 ' + powerUsed + ' / ' + powerTotal + ' W</span><span>' + Math.round(powerUsed / powerTotal * 100) + '%</span></div><div style="height:8px;background:#e1e4e8;border-radius:4px;overflow:hidden;">' + powerBar + '</div></div><div style="margin-bottom:12px;"><div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;"><span>GPU 利用率</span><span>' + util + '%</span></div><div style="height:8px;background:#e1e4e8;border-radius:4px;overflow:hidden;">' + utilBar + '</div></div>';
            }
        })
        .catch(function() {
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败（可能无GPU或nvidia-smi未安装）</div>';
        });
};

function renderProgressBar(current, total, unit) {
    const percent = Math.min(100, Math.max(0, Math.round(current / total * 100)));
    const color = percent > 80 ? '#cf222e' : percent > 50 ? '#d29922' : '#2da44e';
    return '<div style="width:' + percent + '%;height:100%;background:' + color + ';transition:width 0.3s;"></div>';
}

window.openGpuModal = function() { Drawer.open('gpuModal'); loadGpuInfo(); };

// Ollama模型
window.loadOllamaModels = function() {
    const container = document.getElementById('ollamaModelsContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/ollama/models', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload && container) {
                const models = payload.models || [];
                if (models.length === 0) {
                    container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">暂无模型，请先拉取模型</div>';
                    return;
                }
                container.innerHTML = '<div style="display:flex;flex-direction:column;gap:8px;">' +
                    models.map(function(m) {
                        const name = m.name || 'Unknown';
                        const size = m.size || 0;
                        const sizeFormatted = formatSize(size);
                        const isReasoning = name.toLowerCase().includes('qwq') || name.toLowerCase().includes('r1') || name.toLowerCase().includes('reasoning');
                        return '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;"><div style="flex:1;min-width:0;"><div style="font-weight:500;display:flex;align-items:center;gap:8px;">' + (isReasoning ? '<span style="font-size:12px;background:#ddf4ff;color:#0969da;padding:2px 6px;border-radius:4px;">推理</span>' : '') + '<span>' + escapeHtml(name) + '</span></div><div style="font-size:12px;color:#666;margin-top:2px;">' + sizeFormatted + '</div></div><span style="color:#07c160;font-size:18px;">✓</span></div>';
                    }).join('') + '</div>';
            }
        })
        .catch(function() {
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败（Ollama可能未运行）</div>';
        });
};

function formatSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
}

window.openOllamaModal = function() { Drawer.open('ollamaModal'); loadOllamaModels(); };

// OpenClaw配置
window.loadOpenclawConfig = function() {
    const container = document.getElementById('openclawConfigContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/openclaw/config', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload && container) {
                const version = payload.version || 'Unknown';
                const modelCount = payload.models?.count || 0;
                const models = payload.models?.list || [];
                const channels = payload.channels || {};
                const gateway = payload.gateway || {};
                const auth = payload.auth || {};
                
                let html = '<div style="background:#f6f8fa;padding:12px 16px;border-radius:8px;margin-bottom:16px;"><div style="font-size:16px;font-weight:600;">OpenClaw ' + escapeHtml(version) + '</div></div>';
                
                // 模型数量
                html += '<div style="margin-bottom:16px;"><div style="font-size:13px;color:#666;margin-bottom:8px;">模型 (' + modelCount + ')</div><div style="display:flex;flex-direction:column;gap:6px;">';
                models.slice(0, 8).forEach(function(m) {
                    const isReasoning = m.reasoning;
                    html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:6px;padding:8px 12px;font-size:13px;display:flex;align-items:center;gap:8px;">' + (isReasoning ? '<span style="font-size:10px;background:#ddf4ff;color:#0969da;padding:1px 4px;border-radius:3px;">推理</span>' : '') + '<span>' + escapeHtml(m.name || m.id) + '</span></div>';
                });
                if (models.length > 8) {
                    html += '<div style="font-size:12px;color:#666;text-align:center;padding:8px;">...共 ' + modelCount + ' 个模型</div>';
                }
                html += '</div></div>';
                
                // 渠道
                html += '<div style="margin-bottom:16px;"><div style="font-size:13px;color:#666;margin-bottom:8px;">渠道</div><div style="display:flex;flex-wrap:wrap;gap:8px;">';
                Object.entries(channels).forEach(function(cfgs) {
                    const name = cfgs[0];
                    const cfg = cfgs[1];
                    const enabled = cfg.enabled;
                    html += '<span style="font-size:12px;padding:4px 8px;border-radius:4px;background:' + (enabled ? '#dafbe1' : '#ffebe9') + ';color:' + (enabled ? '#1a7f37' : '#cf222e') + ';">' + escapeHtml(name) + ' ' + (enabled ? '✓' : '✗') + '</span>';
                });
                html += '</div></div>';
                
                // 网关
                html += '<div style="margin-bottom:16px;"><div style="font-size:13px;color:#666;margin-bottom:8px;">网关</div><div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;"><div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span>端口</span><span style="font-family:monospace;">' + (gateway.port || '-') + '</span></div><div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span>绑定</span><span>' + (gateway.bind || '-') + '</span></div><div style="display:flex;justify-content:space-between;"><span>Tailscale</span><span style="color:' + (gateway.tailscale === 'off' ? '#cf222e' : '#07c160') + ';">' + (gateway.tailscale || '-') + '</span></div></div></div>';
                
                container.innerHTML = html;
            }
        })
        .catch(function() {
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败</div>';
        });
};

window.openOpenclawModal = function() { Drawer.open('openclawModal'); loadOpenclawConfig(); };
