// ============ 系统监控加载函数模块 ============
/* global fetch, escapeHtml, Drawer, loadGitList, loadProcessList, loadSystemPackageList, loadPipList, loadNpmList, loadDockerTabs, loadSystemdList, loadDiskList, loadNetworkList, authHeaders */

///<reference path="../globals.d.ts" />

function apiData(resp) {
    return resp && resp.success ? resp.data : null;
}

// 进程管理
window.loadProcessList = function() {
    const container = document.getElementById('processListContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/process/list', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload) {
                const container = document.getElementById('processListContainer');
                if (container && payload.processes) {
                    let html = '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f6f8fa;"><th style="padding:8px;text-align:left;">PID</th><th style="padding:8px;text-align:left;">名称</th><th style="padding:8px;text-align:left;">CPU</th><th style="padding:8px;text-align:left;">内存</th><th style="padding:8px;text-align:left;">端口</th></tr></thead><tbody>';
                    payload.processes.slice(0,50).forEach(p => {
                        html += `<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;">${p.pid}</td><td style="padding:8px;font-family:monospace;">${p.name || '?'}</td><td style="padding:8px;">${p.cpu}%</td><td style="padding:8px;">${p.memory}%</td><td style="padding:8px;">${p.ports ? p.ports.join(', ') : '-'}</td></tr>`;
                    });
                    html += '</tbody></table>';
                    container.innerHTML = html;
                }
            }
        });
};

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
                        html += `<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;">${p.name}</td><td style="padding:8px;">${p.version}</td></tr>`;
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
                        html += `<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;">${p.name}</td><td style="padding:8px;">${p.version}</td></tr>`;
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
                        html += `<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;">${p.name}</td><td style="padding:8px;">${p.version}</td></tr>`;
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
                        html += `<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;font-family:monospace;">${img.repository || img.tag || '?'}</td><td style="padding:8px;font-family:monospace;font-size:12px;">${img.id?.substring(0,12)}</td><td style="padding:8px;">${img.size}</td><td style="padding:8px;">${img.created}</td></tr>`;
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
                        html += `<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;font-family:monospace;">${c.names || c.id?.substring(0,12)}</td><td style="padding:8px;color:${c.state==='running'?'#07c160':'#cf222e'}">${c.state}</td><td style="padding:8px;">${c.image}</td></tr>`;
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
                        const isRunning = s.active?.includes('active');
                        const timeAgo = formatTimeAgo(s.active_since);
                        html += `<tr style="border-bottom:1px solid #eee;">
                            <td style="padding:8px;font-family:monospace;font-size:12px;">
                                ${s.name.replace('.service', '')}
                                ${timeAgo ? '<br><span style="color:#666;font-size:11px;">' + timeAgo + '</span>' : ''}
                            </td>
                            <td style="padding:8px;color:${isRunning ? '#07c160' : '#cf222e'}">${s.status || '-'}</td>
                            <td style="padding:8px;">${s.enabled ? '✓' : '✗'}</td>
                            <td style="padding:8px;">
                                <button onclick="controlSystemdService('${s.name}', 'start')" style="background:#07c160;color:#fff;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;margin-right:4px;font-size:11px;" title="启动">▶</button>
                                <button onclick="controlSystemdService('${s.name}', 'stop')" style="background:#cf222e;color:#fff;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;margin-right:4px;font-size:11px;" title="停止">⏹</button>
                                <button onclick="controlSystemdService('${s.name}', 'restart')" style="background:#0969da;color:#fff;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px;" title="重启">🔄</button>
                            </td>
                        </tr>`;
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
            const mins = Math.floor(diffSecs / 60);
            return mins + 'm ago';
        } else if (diffSecs < 86400) {
            const hours = Math.floor(diffSecs / 3600);
            return hours + 'h ago';
        } else {
            const days = Math.floor(diffSecs / 86400);
            return days + 'd ago';
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
                        html += `<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;">${d.device}</td><td style="padding:8px;">${d.total}</td><td style="padding:8px;">${d.used}</td><td style="padding:8px;">${d.available}</td><td style="padding:8px;">${d.mountpoint}</td></tr>`;
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
                        html += `<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;">${i.name}</td><td style="padding:8px;color:${i.state === 'UP' ? '#07c160' : '#cf222e'}">${i.state}</td><td style="padding:8px;">${i.ipv4 || '-'}</td><td style="padding:8px;">${i.mac || '-'}</td></tr>`;
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
                    let html = '';
                    payload.repos.forEach(repo => {
                        const branch = repo.status ? repo.status.branch : '-';
                        html += `<div style="margin-bottom:16px;">
                            <div style="background:#f6f8fa;padding:8px 12px;border-radius:6px 6px 0 0;display:flex;justify-content:space-between;align-items:center;border:1px solid #d0d7de;border-bottom:none;">
                                <span style="font-weight:600;font-size:14px;">${repo.name}</span>
                                <span style="background:#ddf4ff;color:#0969da;padding:2px 8px;border-radius:10px;font-size:11px;">${branch}</span>
                            </div>
                            <div style="background:#fff;border:1px solid #d0d7de;border-radius:0 0 6px 6px;max-height:300px;overflow-y:auto;">`;
                        if (repo.logs && repo.logs.length > 0) {
                            repo.logs.slice(0, 15).forEach((log, idx) => {
                                const bg = idx % 2 === 0 ? '#fff' : '#f6f8fa';
                                html += `<div style="padding:6px 10px;background:${bg};display:flex;align-items:center;font-size:12px;line-height:1.4;border-top:1px solid #eee;">
                                    <span style="color:#0969da;font-family:monospace;font-size:11px;width:70px;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;">${log.hash}</span>
                                    <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(log.message)}</span>
                                </div>`;
                            });
                        } else {
                            html += '<div style="padding:16px;text-align:center;color:#666;">暂无提交记录</div>';
                        }
                        html += `</div></div>`;
                    });
                    container.innerHTML = html;
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
                
                container.innerHTML = `
                    <div style="background:#f6f8fa;padding:12px 16px;border-radius:8px;margin-bottom:12px;">
                        <div style="font-size:18px;font-weight:600;margin-bottom:4px;">${escapeHtml(gpuName)}</div>
                        <div style="font-size:12px;color:#666;">驱动: ${escapeHtml(driver)} | CUDA: ${escapeHtml(cuda)}</div>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:16px;">
                        <div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center;">
                            <div style="font-size:24px;font-weight:600;color:${temp > 70 ? '#cf222e' : '#24292f'}">${temp}°C</div>
                            <div style="font-size:12px;color:#666;margin-top:4px;">温度</div>
                        </div>
                        <div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center;">
                            <div style="font-size:24px;font-weight:600;color:#24292f">${util}%</div>
                            <div style="font-size:12px;color:#666;margin-top:4px;">利用率</div>
                        </div>
                    </div>
                    <div style="margin-bottom:12px;">
                        <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;">
                            <span>显存 ${memoryUsed} / ${memoryTotal} MiB</span>
                            <span>${memoryPercent}%</span>
                        </div>
                        <div style="height:8px;background:#e1e4e8;border-radius:4px;overflow:hidden;">${memoryBar}</div>
                    </div>
                    <div style="margin-bottom:12px;">
                        <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;">
                            <span>功耗 ${powerUsed} / ${powerTotal} W</span>
                            <span>${Math.round(powerUsed / powerTotal * 100)}%</span>
                        </div>
                        <div style="height:8px;background:#e1e4e8;border-radius:4px;overflow:hidden;">${powerBar}</div>
                    </div>
                    <div style="margin-bottom:12px;">
                        <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;">
                            <span>GPU 利用率</span>
                            <span>${util}%</span>
                        </div>
                        <div style="height:8px;background:#e1e4e8;border-radius:4px;overflow:hidden;">${utilBar}</div>
                    </div>
                `;
            }
        })
        .catch(function() {
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败（可能无GPU或nvidia-smi未安装）</div>';
        });
};

function renderProgressBar(current, total, unit) {
    const percent = Math.min(100, Math.max(0, Math.round(current / total * 100)));
    const color = percent > 80 ? '#cf222e' : percent > 50 ? '#d29922' : '#2da44e';
    return `<div style="width:${percent}%;height:100%;background:${color};transition:width 0.3s;"></div>`;
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
                        return `<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;">
                            <div style="flex:1;min-width:0;">
                                <div style="font-weight:500;display:flex;align-items:center;gap:8px;">
                                    ${isReasoning ? '<span style="font-size:12px;background:#ddf4ff;color:#0969da;padding:2px 6px;border-radius:4px;">推理</span>' : ''}
                                    <span>${escapeHtml(name)}</span>
                                </div>
                                <div style="font-size:12px;color:#666;margin-top:2px;">${sizeFormatted}</div>
                            </div>
                            <span style="color:#07c160;font-size:18px;">✓</span>
                        </div>`;
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
                
                let html = `<div style="background:#f6f8fa;padding:12px 16px;border-radius:8px;margin-bottom:16px;">
                    <div style="font-size:16px;font-weight:600;">OpenClaw ${escapeHtml(version)}</div>
                </div>`;
                
                // 模型数量
                html += `<div style="margin-bottom:16px;">
                    <div style="font-size:13px;color:#666;margin-bottom:8px;">模型 (${modelCount})</div>
                    <div style="display:flex;flex-direction:column;gap:6px;">`;
                models.slice(0, 8).forEach(function(m) {
                    const isReasoning = m.reasoning;
                    html += `<div style="background:#fff;border:1px solid #d0d7de;border-radius:6px;padding:8px 12px;font-size:13px;display:flex;align-items:center;gap:8px;">
                        ${isReasoning ? '<span style="font-size:10px;background:#ddf4ff;color:#0969da;padding:1px 4px;border-radius:3px;">推理</span>' : ''}
                        <span>${escapeHtml(m.name || m.id)}</span>
                    </div>`;
                });
                if (models.length > 8) {
                    html += `<div style="font-size:12px;color:#666;text-align:center;padding:8px;">...共 ${modelCount} 个模型</div>`;
                }
                html += `</div></div>`;
                
                // 渠道
                html += `<div style="margin-bottom:16px;">
                    <div style="font-size:13px;color:#666;margin-bottom:8px;">渠道</div>
                    <div style="display:flex;flex-wrap:wrap;gap:8px;">`;
                Object.entries(channels).forEach(function([name, cfg]) {
                    const enabled = cfg.enabled;
                    html += `<span style="font-size:12px;padding:4px 8px;border-radius:4px;background:${enabled ? '#dafbe1' : '#ffebe9'};color:${enabled ? '#1a7f37' : '#cf222e'};">
                        ${escapeHtml(name)} ${enabled ? '✓' : '✗'}
                    </span>`;
                });
                html += `</div></div>`;
                
                // 网关
                html += `<div style="margin-bottom:16px;">
                    <div style="font-size:13px;color:#666;margin-bottom:8px;">网关</div>
                    <div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                            <span>端口</span>
                            <span style="font-family:monospace;">${gateway.port || '-'}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                            <span>绑定</span>
                            <span>${gateway.bind || '-'}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;">
                            <span>Tailscale</span>
                            <span style="color:${gateway.tailscale === 'off' ? '#cf222e' : '#07c160'};">${gateway.tailscale || '-'}</span>
                        </div>
                    </div>
                </div>`;
                
                container.innerHTML = html;
            }
        })
        .catch(function() {
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败</div>';
        });
};

window.openOpenclawModal = function() { Drawer.open('openclawModal'); loadOpenclawConfig(); };
