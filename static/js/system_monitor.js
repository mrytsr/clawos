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
