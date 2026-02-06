// ============ 系统监控加载函数模块 ============
/* global fetch, escapeHtml, Drawer, loadGitList, loadProcessList, loadSystemPackageList, loadPipList, loadNpmList, loadDockerTabs, loadSystemdList, loadDiskList, loadNetworkList, loadGpuInfo, loadOllamaModels, loadOpenclawConfig, formatBytes, sortProcesses, filterProcesses, showProcessDetail, authHeaders */

///<reference path="../globals.d.ts" />

function apiData(resp) {
    return resp && resp.success ? resp.data : null;
}

function formatBytes(bytes) {
    bytes = Number(bytes) || 0;
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB';
    return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB';
}

// 进程管理
window.loadProcessList = function() {
    const container = document.getElementById('processListContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/process/list', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload && container) {
                const stats = payload.stats || {};
                const processes = payload.processes || [];
                
                const memUsed = formatBytes(stats.memory_used || 0);
                const memTotal = formatBytes(stats.memory_total || 1);
                const memPercent = stats.memory_percent || 0;
                const cpuPercent = stats.cpu_percent || 0;
                const processCount = stats.process_count || 0;
                
                const statsHtml = '<div style="display:flex;flex-wrap:wrap;gap:8px;padding:12px;background:#f6f8fa;border-bottom:1px solid #eee;">' +
                    '<span>💻 CPU: ' + cpuPercent + '%</span>' +
                    '<span>🧠 ' + memUsed + '/' + memTotal + ' (' + memPercent + '%)</span>' +
                    '<span>📊 ' + processCount + ' 进程</span>' +
                    '</div>' +
                    '<div style="display:flex;gap:8px;padding:8px 12px;border-bottom:1px solid #eee;">' +
                    '<select id="processSortSelect" onchange="sortProcesses(this.value)" style="flex:1;padding:8px;border:1px solid #ddd;border-radius:6px;font-size:13px;">' +
                    '<option value="cpu" selected>按 CPU 使用率</option>' +
                    '<option value="memory">按内存使用率</option>' +
                    '<option value="pid">按 PID</option>' +
                    '<option value="name">按进程名</option>' +
                    '</select>' +
                    '<input type="text" id="processSearchInput" ' +
                    'placeholder="🔍 搜索..." ' +
                    'oninput="filterProcesses()" ' +
                    'style="flex:2;padding:8px;border:1px solid #ddd;border-radius:6px;font-size:13px;">' +
                    '</div>' +
                    '<div id="processCardsContainer"></div>';
                
                container.innerHTML = statsHtml;
                
                window._processData = processes;
                renderProcessCards(processes.slice(0, 100), 'cpu');
            }
        })
        .catch(function() {
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败</div>';
        });
};

function renderProcessCards(processList, sortBy) {
    const cardsContainer = document.getElementById('processCardsContainer');
    if (!cardsContainer) return;
    
    const sorted = processList.slice().sort(function(a, b) {
        if (sortBy === 'cpu') return (b.cpu_percent || 0) - (a.cpu_percent || 0);
        if (sortBy === 'memory') return (b.memory_percent || 0) - (a.memory_percent || 0);
        if (sortBy === 'pid') return (a.pid || 0) - (b.pid || 0);
        if (sortBy === 'name') return (a.command || '').localeCompare(b.command || '');
        return 0;
    });
    
    const limited = sorted.slice(0, 100);
    
    if (limited.length === 0) {
        cardsContainer.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">没有找到进程</div>';
        return;
    }
    
    cardsContainer.innerHTML = limited.map(function(p, index) {
        return renderProcessCard(p, index + 1);
    }).join('');
}

window.sortProcesses = function(sortBy) {
    if (!window._processData) return;
    const searchKeyword = document.getElementById('processSearchInput').value.toLowerCase();
    let filtered = window._processData;
    if (searchKeyword) {
        filtered = window._processData.filter(function(p) {
            return (p.command || '').toLowerCase().includes(searchKeyword) || 
                   (p.full_command || '').toLowerCase().includes(searchKeyword);
        });
    }
    renderProcessCards(filtered, sortBy);
};

window.filterProcesses = function() {
    const sortBy = document.getElementById('processSortSelect').value;
    sortProcesses(sortBy);
};

function renderProcessCard(p, index) {
    const cpuPercent = p.cpu_percent || 0;
    const memPercent = p.memory_percent || 0;
    const command = p.command || '?';
    const fullCommand = p.full_command || command;
    const pid = p.pid || 0;
    const elapsed = p.elapsed || '0:00';
    const icon = getProcessIcon(command);
    const ports = p.ports || [];
    
    let cpuColor = '#07c160';
    if (cpuPercent > 80) cpuColor = '#cf222e';
    else if (cpuPercent > 50) cpuColor = '#d29922';
    
    let displayPath = fullCommand;
    if (displayPath.length > 50) displayPath = displayPath.substring(0, 50) + '...';
    
    return '<div class="process-card" data-name="' + (p.command || '').toLowerCase() + '" onclick="showProcessDetail(' + pid + ')" style="cursor:pointer;padding:12px;border-bottom:1px solid #eee;">' +
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">' +
        '<span style="color:#999;font-size:12px;width:24px;">' + index + '.</span>' +
        '<span>' + icon + '</span>' +
        '<span style="font-weight:500;font-size:14px;flex:1;">' + escapeHtml(command) + '</span>' +
        (cpuPercent > 0 ? '<span style="font-size:12px;color:#666;">' + cpuPercent.toFixed(1) + '%</span>' : '') +
        '</div>' +
        '<div style="height:4px;background:#e1e4e8;border-radius:2px;overflow:hidden;margin:6px 0 4px 32px;">' +
        '<div style="height:100%;width:' + cpuPercent + '%;background-color:' + cpuColor + ';border-radius:2px;"></div>' +
        '</div>' +
        '<div style="display:flex;flex-wrap:wrap;gap:8px;font-size:11px;color:#666;margin-left:32px;">' +
        '<span>💭 ' + memPercent.toFixed(1) + '%</span>' +
        '<span>⏱️ ' + elapsed + '</span>' +
        '<span>👤 ' + escapeHtml(p.user || '?') + '</span>' +
        '<span style="font-family:monospace;">PID:' + pid + '</span>' +
        '</div>' +
        '</div>';
}

window.showProcessDetail = function(pid) {
    if (!window._processData) return;
    const p = window._processData.find(function(proc) { return proc.pid === pid; });
    if (!p) return;
    
    const detailHtml = '<div style="padding:16px;">' +
        '<h3 style="margin:0 0 16px 0;font-size:16px;">' + getProcessIcon(p.name || '') + ' ' + escapeHtml(p.name || '?') + '</h3>' +
        '<div style="font-size:13px;line-height:1.8;">' +
        '<div><span style="color:#666;">PID:</span> ' + p.pid + '</div>' +
        '<div><span style="color:#666;">CPU:</span> ' + (p.cpu || 0).toFixed(1) + '%</div>' +
        '<div><span style="color:#666;">内存:</span> ' + (p.memory || 0).toFixed(1) + '%</div>' +
        '<div><span style="color:#666;">CPU:</span> ' + (p.cpu_percent || 0).toFixed(1) + '%</div>' +
        '<div><span style="color:#666;">内存:</span> ' + (p.memory_percent || 0).toFixed(1) + '%</div>' +
        '<div><span style="color:#666;">运行时长:</span> ' + (p.elapsed || '-') + '</div>' +
        '<div><span style="color:#666;">用户:</span> ' + (p.user || '-') + '</div>' +
        '<div style="margin-top:12px;"><span style="color:#666;">命令:</span><br><code style="font-size:11px;word-break:break-all;background:#f6f8fa;padding:8px;border-radius:4px;display:block;margin-top:4px;">' + escapeHtml(p.full_command || '-') + '</code></div>' +
        '</div>' +
        '</div>';
    
    document.getElementById('processDetailContent').innerHTML = detailHtml;
    Drawer.open('processDetailModal');
};

function getProcessIcon(cmd) {
    var lower = (cmd || '').toLowerCase();
    var icons = {
        'chrome': '🚀',
        'firefox': '🦊',
        'python': '🐍',
        'python3': '🐍',
        'node': '📦',
        'npm': '📦',
        'pnpm': '📦',
        'ssh': '🔐',
        'docker': '🐳',
        'nginx': '🌐',
        'apache': '🌐',
        'systemd': '⚙️',
        'mysqld': '🗄️',
        'postgres': '🗄️',
        'redis': '🔴',
        'file_server': '📁',
        'claws': '🦞',
        'openclaw': '🦞',
    };
    for (var key in icons) {
        if (icons.hasOwnProperty(key) && lower.includes(key)) {
            return icons[key];
        }
    }
    return '⚫';
}

// 系统包管理
window.loadSystemPackageList = function() {
    const container = document.getElementById('systemPackageListContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...（系统包较多，请稍候）</div>';
    fetch('/api/system-packages/list', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload) {
                const container = document.getElementById('systemPackageListContainer');
                if (container && payload.packages) {
                    let html = '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f6f8fa;"><th style="padding:8px;text-align:left;">包名</th><th style="padding:8px;text-align:left;">版本</th></tr></thead><tbody>';
                    payload.packages.slice(0,100).forEach(p => {
                        html += '<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;">' + p.name + '</td><td style="padding:8px;">' + p.version + '</td></tr>';
                    });
                    html += '</tbody></table>';
                    container.innerHTML = html;
                }
            }
        });
};

// Pip 包管理
window.loadPipList = function() {
    const container = document.getElementById('pipListContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/pip/list', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload) {
                const container = document.getElementById('pipListContainer');
                if (container && payload.packages) {
                    let html = '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f6f8fa;"><th style="padding:8px;text-align:left;">包名</th><th style="padding:8px;text-align:left;">版本</th></tr></thead><tbody>';
                    payload.packages.slice(0,100).forEach(p => {
                        html += '<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;">' + p.name + '</td><td style="padding:8px;">' + p.version + '</td></tr>';
                    });
                    html += '</tbody></table>';
                    container.innerHTML = html;
                }
            }
        });
};

// NPM 包管理
window.loadNpmList = function() {
    const container = document.getElementById('npmListContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/npm/list', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload) {
                const container = document.getElementById('npmListContainer');
                if (container && payload.packages) {
                    let html = '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f6f8fa;"><th style="padding:8px;text-align:left;">包名</th><th style="padding:8px;text-align:left;">版本</th></tr></thead><tbody>';
                    payload.packages.slice(0,100).forEach(p => {
                        html += '<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;">' + p.name + '</td><td style="padding:8px;">' + p.version + '</td></tr>';
                    });
                    html += '</tbody></table>';
                    container.innerHTML = html;
                }
            }
        });
};

// Docker 标签切换
window.loadDockerTabs = function(tab) {
    const imagesContainer = document.getElementById('dockerImagesContainer');
    const containersContainer = document.getElementById('dockerContainersContainer');
    
    if (tab === 'images') {
        imagesContainer.style.display = 'block';
        containersContainer.style.display = 'none';
        if (imagesContainer) imagesContainer.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
        fetch('/api/docker/images', { headers: authHeaders() })
            .then(r => r.json())
            .then(data => {
                const payload = apiData(data);
                if (payload && imagesContainer && payload.images) {
                    let html = '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f6f8fa;"><th style="padding:8px;text-align:left;">镜像</th><th style="padding:8px;text-align:left;">ID</th><th style="padding:8px;text-align:left;">大小</th><th style="padding:8px;text-align:left;">创建时间</th></tr></thead><tbody>';
                    payload.images.forEach(img => {
                        html += '<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;font-family:monospace;">' + (img.repository || img.tag || '?') + '</td><td style="padding:8px;font-family:monospace;font-size:12px;">' + (img.id ? img.id.substring(0,12) : '') + '</td><td style="padding:8px;">' + img.size + '</td><td style="padding:8px;">' + img.created + '</td></tr>';
                    });
                    html += '</tbody></table>';
                    imagesContainer.innerHTML = html;
                }
            });
    } else {
        imagesContainer.style.display = 'none';
        containersContainer.style.display = 'block';
        if (containersContainer) containersContainer.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
        fetch('/api/docker/containers', { headers: authHeaders() })
            .then(r => r.json())
            .then(data => {
                const payload = apiData(data);
                if (payload && containersContainer && payload.containers) {
                    let html = '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f6f8fa;"><th style="padding:8px;text-align:left;">容器</th><th style="padding:8px;text-align:left;">状态</th><th style="padding:8px;text-align:left;">镜像</th></tr></thead><tbody>';
                    payload.containers.forEach(c => {
                        html += '<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;font-family:monospace;">' + (c.names || (c.id ? c.id.substring(0,12) : '')) + '</td><td style="padding:8px;color:' + (c.state==='running'?'#07c160':'#cf222e') + '">' + c.state + '</td><td style="padding:8px;">' + c.image + '</td></tr>';
                    });
                    html += '</tbody></table>';
                    containersContainer.innerHTML = html;
                }
            });
    }
};

// Systemd 服务
window.loadSystemdList = function() {
    const container = document.getElementById('systemdListContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/systemd/list', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload) {
                const container = document.getElementById('systemdListContainer');
                if (container && payload.services) {
                    let html = '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f6f8fa;"><th style="padding:8px;text-align:left;">服务</th><th style="padding:8px;text-align:left;">状态</th><th style="padding:8px;text-align:left;">自启</th><th style="padding:8px;text-align:left;">操作</th></tr></thead><tbody>';
                    payload.services.slice(0,50).forEach(s => {
                        const isRunning = s.active && s.active.includes('active');
                        const timeAgo = formatTimeAgo(s.active_since);
                        html += '<tr style="border-bottom:1px solid #eee;">' +
                            '<td style="padding:8px;font-family:monospace;font-size:12px;">' + s.name.replace('.service', '') + (timeAgo ? '<br><span style="color:#666;font-size:11px;">' + timeAgo + '</span>' : '') + '</td>' +
                            '<td style="padding:8px;color:' + (isRunning ? '#07c160' : '#cf222e') + '">' + (s.status || '-') + '</td>' +
                            '<td style="padding:8px;">' + (s.enabled ? '✓' : '✗') + '</td>' +
                            '<td style="padding:8px;">' +
                            '<button onclick="controlSystemdService(\'' + s.name + '\', \'start\')" style="background:#07c160;color:#fff;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;margin-right:4px;font-size:11px;" title="启动">▶</button>' +
                            '<button onclick="controlSystemdService(\'' + s.name + '\', \'stop\')" style="background:#cf222e;color:#fff;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;margin-right:4px;font-size:11px;" title="停止">⏹</button>' +
                            '<button onclick="controlSystemdService(\'' + s.name + '\', \'restart\')" style="background:#0969da;color:#fff;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px;" title="重启">🔄</button>' +
                            '</td>' +
                            '</tr>';
                    });
                    html += '</tbody></table>';
                    container.innerHTML = html;
                }
            }
        });
};

// 格式化时间差
function formatTimeAgo(isoTime) {
    if (!isoTime) return null;
    try {
        const start = new Date(isoTime);
        const now = new Date();
        const diffMs = now - start;
        const diffSecs = Math.floor(diffMs / 1000);
        
        if (diffSecs < 60) {
            return diffSecs + 's ago';
        } else if (diffSecs < 3600) {
            return Math.floor(diffSecs / 60) + 'm ago';
        } else if (diffSecs < 86400) {
            return Math.floor(diffSecs / 3600) + 'h ago';
        } else {
            return Math.floor(diffSecs / 86400) + 'd ago';
        }
    } catch (e) {
        return null;
    }
}

window.controlSystemdService = function(service, action) {
    (async () => {
        if (!window.TaskActions || typeof window.TaskActions.controlSystemdService !== 'function') {
            showToast('操作失败', 'error');
            return;
        }
        const result = await window.TaskActions.controlSystemdService(service, action);
        if (result && result.ok) loadSystemdList();
    })();
};

// 磁盘管理
window.loadDiskList = function() {
    const container = document.getElementById('diskListContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/disk/list', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload) {
                const container = document.getElementById('diskListContainer');
                if (container && payload.disks) {
                    let html = '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f6f8fa;"><th style="padding:8px;text-align:left;">设备</th><th style="padding:8px;text-align:left;">总计</th><th style="padding:8px;text-align:left;">已用</th><th style="padding:8px;text-align:left;">可用</th><th style="padding:8px;text-align:left;">挂载点</th></tr></thead><tbody>';
                    payload.disks.forEach(d => {
                        html += '<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;">' + d.device + '</td><td style="padding:8px;">' + d.total + '</td><td style="padding:8px;">' + d.used + '</td><td style="padding:8px;">' + d.available + '</td><td style="padding:8px;">' + d.mountpoint + '</td></tr>';
                    });
                    html += '</tbody></table>';
                    container.innerHTML = html;
                }
            }
        });
};

// 网络管理
window.loadNetworkList = function() {
    const container = document.getElementById('networkListContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/network/list', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload) {
                const container = document.getElementById('networkListContainer');
                if (container && payload.interfaces) {
                    let html = '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f6f8fa;"><th style="padding:8px;text-align:left;">接口</th><th style="padding:8px;text-align:left;">状态</th><th style="padding:8px;text-align:left;">IPV4</th><th style="padding:8px;text-align:left;">MAC</th></tr></thead><tbody>';
                    payload.interfaces.forEach(i => {
                        html += '<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;">' + i.name + '</td><td style="padding:8px;color:' + (i.state === 'UP' ? '#07c160' : '#cf222e') + '">' + i.state + '</td><td style="padding:8px;">' + (i.ipv4 || '-') + '</td><td style="padding:8px;">' + (i.mac || '-') + '</td></tr>';
                    });
                    html += '</tbody></table>';
                    container.innerHTML = html;
                }
            }
        });
};

// Git 管理（手机适配版）
window.loadGitList = function() {
    const container = document.getElementById('gitListContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:20px;color:#666;">🔄 加载中...</div>';
    fetch('/api/git/list', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload && payload.repos) {
                const container = document.getElementById('gitListContainer');
                if (container) {
                    window.__gitRepos = payload.repos || [];
                    const css = '<style>.git-shell { display:flex; flex-direction:column; gap:10px; }.git-top { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }.git-top .label { font-size:12px; color:#57606a; }.git-select { padding:6px 10px; border:1px solid #d0d7de; border-radius:8px; background:#fff; font-size:13px; }.git-layout { display:grid; grid-template-columns: 190px 1fr; gap:10px; min-height: 340px; }.git-left { border:1px solid #d0d7de; border-radius:10px; overflow:hidden; background:#fff; }.git-right { border:1px solid #d0d7de; border-radius:10px; overflow:hidden; background:#fff; display:flex; flex-direction:column; }.git-hd { background:#f6f8fa; border-bottom:1px solid #d0d7de; padding:10px 12px; display:flex; justify-content:space-between; align-items:center; gap:10px; }.git-hd .title { font-weight:600; font-size:13px; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.git-hd .meta { font-size:11px; color:#57606a; display:flex; gap:8px; align-items:center; }.git-list { max-height: 340px; overflow:auto; }.git-item { padding:8px 10px; border-top:1px solid #eee; cursor:pointer; display:flex; flex-direction:column; gap:3px; }.git-item:hover { background:#f6f8fa; }.git-item.active { background:#ddf4ff; }.git-time { font-size:12px; color:#0969da; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }.git-hash { font-size:11px; color:#57606a; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; text-decoration:underline; cursor:pointer; width: fit-content; }.git-hash:hover { color:#0969da; }.git-subject { font-size:12px; color:#24292f; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.git-detail { padding:12px; overflow:auto; }.git-detail pre { margin:0; font-size:12px; line-height:1.45; white-space:pre-wrap; word-break:break-word; overflow-wrap:anywhere; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }.git-actions { display:flex; gap:8px; align-items:center; }.git-btn { background:#fff; border:1px solid #d0d7de; border-radius:8px; font-size:12px; padding:5px 8px; cursor:pointer; }.git-btn:hover { background:#f6f8fa; }@media (max-width: 520px) { .git-layout { grid-template-columns: 1fr; } .git-left { max-height: 260px; } }</style>';
                    const html = css + '<div class="git-shell"><div class="git-top"><span class="label">仓库</span><select id="gitRepoSelect" class="git-select"></select></div><div class="git-layout"><div class="git-left"><div class="git-hd"><div class="title" id="gitRepoTitle">提交列表</div><div class="meta" id="gitRepoMeta"></div></div><div class="git-list" id="gitCommitList"></div></div><div class="git-right"><div class="git-hd"><div class="title" id="gitCommitTitle">提交详情</div><div class="git-actions"><button class="git-btn" type="button" id="gitCopyHashBtn" disabled>复制哈希</button><button class="git-btn" type="button" id="gitOpenNewTabBtn" disabled>新标签页</button></div></div><div class="git-detail"><pre id="gitCommitSummary">请选择左侧提交</pre></div></div></div></div>';
                    container.innerHTML = html;

                    const repos = window.__gitRepos || [];
                    const select = document.getElementById('gitRepoSelect');
                    const repoTitle = document.getElementById('gitRepoTitle');
                    const repoMeta = document.getElementById('gitRepoMeta');
                    const listEl = document.getElementById('gitCommitList');
                    const summaryEl = document.getElementById('gitCommitSummary');
                    const commitTitle = document.getElementById('gitCommitTitle');
                    const copyBtn = document.getElementById('gitCopyHashBtn');
                    const openBtn = document.getElementById('gitOpenNewTabBtn');

                    const state = { repoId: null, hash: null };

                    function commitPageUrl(repoId, hash) {
                        return '/git/commit?repoId=' + encodeURIComponent(repoId) + '&hash=' + encodeURIComponent(hash);
                    }

                    function setSelected(repoId, hash, committedAt) {
                        state.repoId = repoId;
                        state.hash = hash;
                        commitTitle.textContent = committedAt ? committedAt : '提交详情';
                        copyBtn.disabled = !hash;
                        openBtn.disabled = !hash;
                        summaryEl.textContent = '🔄 加载中...';
                        fetch('/api/git/commit?repoId=' + encodeURIComponent(repoId) + '&hash=' + encodeURIComponent(hash) + '&include=summary', { headers: authHeaders() })
                            .then(r => r.json())
                            .then(d => {
                                const p = apiData(d);
                                summaryEl.textContent = (p && p.log) ? p.log : '加载失败';
                            })
                            .catch(function() { summaryEl.textContent = '加载失败'; });
                    }

                    function renderRepo(repo) {
                        if (!repo) return;
                        state.repoId = repo.id;
                        const branch = repo.status ? repo.status.branch : '-';
                        repoTitle.textContent = repo.name;
                        repoMeta.innerHTML = '<span style="background:#ddf4ff;color:#0969da;padding:2px 8px;border-radius:999px;font-size:11px;">' + escapeHtml(branch) + '</span>';

                        const logs = Array.isArray(repo.logs) ? repo.logs : [];
                        if (logs.length === 0) {
                            listEl.innerHTML = '<div style="padding:16px;text-align:center;color:#666;">暂无提交记录</div>';
                            summaryEl.textContent = '暂无提交记录';
                            copyBtn.disabled = true;
                            openBtn.disabled = true;
                            return;
                        }
                        listEl.innerHTML = logs.map(function(log, idx) {
                            const time = escapeHtml(log.committed_at || '');
                            const subject = escapeHtml(log.subject || '');
                            const shortHash = escapeHtml(String(log.hash || '').slice(0, 7));
                            const activeCls = idx === 0 ? 'active' : '';
                            return '<div class="git-item ' + activeCls + '" data-hash="' + escapeHtml(log.hash) + '" data-time="' + time + '"><div class="git-time">' + time + '</div><div class="git-hash" data-open="1">' + shortHash + '</div><div class="git-subject" title="' + subject + '">' + (subject || '-') + '</div></div>';
                        }).join('');

                        const first = logs[0];
                        setSelected(repo.id, first.hash, first.committed_at);
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

                    listEl.addEventListener('click', function(ev) {
                        const t = (ev && ev.target && ev.target.nodeType === 3) ? ev.target.parentElement : (ev ? ev.target : null);
                        const open = !!(t && t.closest && t.closest('[data-open="1"]'));
                        const item = t && t.closest ? t.closest('.git-item') : null;
                        if (!item) return;
                        const hash = item.getAttribute('data-hash');
                        const time = item.getAttribute('data-time');
                        const repoId = state.repoId;
                        if (!repoId || !hash) return;

                        Array.from(listEl.querySelectorAll('.git-item')).forEach(function(el) { el.classList.remove('active'); });
                        item.classList.add('active');
                        setSelected(repoId, hash, time);

                        if (open) {
                            ev.preventDefault();
                            ev.stopPropagation();
                            const url = commitPageUrl(repoId, hash);
                            const win = window.open(url, '_blank');
                            if (!win) window.location.assign(url);
                        }
                    });

                    copyBtn.addEventListener('click', function() {
                        if (!state.hash) return;
                        const hash = state.hash;
                        const done = function() {
                            const old = copyBtn.textContent;
                            copyBtn.textContent = '已复制';
                            setTimeout(function() { copyBtn.textContent = old; }, 900);
                        };
                        if (navigator.clipboard && navigator.clipboard.writeText) {
                            navigator.clipboard.writeText(hash).then(done).catch(function() {
                                try {
                                    const ta = document.createElement('textarea');
                                    ta.value = hash;
                                    document.body.appendChild(ta);
                                    ta.select();
                                    document.execCommand('copy');
                                    document.body.removeChild(ta);
                                    done();
                                } catch (e) {}
                            });
                        } else {
                            try {
                                const ta = document.createElement('textarea');
                                ta.value = hash;
                                document.body.appendChild(ta);
                                ta.select();
                                document.execCommand('copy');
                                document.body.removeChild(ta);
                                done();
                            } catch (e) {}
                        }
                    });

                    openBtn.addEventListener('click', function() {
                        if (!state.repoId || !state.hash) return;
                        window.open(commitPageUrl(state.repoId, state.hash), '_blank');
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
