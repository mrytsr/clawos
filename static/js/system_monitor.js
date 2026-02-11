function apiData(resp) {
    if (!resp || typeof resp !== 'object') return null;
    if (resp.success && resp.data && typeof resp.data === 'object') return resp.data;
    return null;
}

function __setContainerHtml(id, html) {
    const el = document.getElementById(id);
    if (!el) return null;
    el.innerHTML = html;
    return el;
}

function __loadingHtml(label) {
    return '<div style="text-align:center;padding:40px;color:#666;">🔄 ' + escapeHtml(label || '加载中...') + '</div>';
}

function __emptyHtml(label) {
    return '<div style="text-align:center;padding:40px;color:#666;">' + escapeHtml(label || '暂无数据') + '</div>';
}

function __errorHtml(label) {
    return '<div style="text-align:center;padding:40px;color:#cf222e;">' + escapeHtml(label || '加载失败') + '</div>';
}

function __postJson(url, payload) {
    return fetch(url, {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, (typeof authHeaders === 'function') ? authHeaders() : {}),
        body: JSON.stringify(payload || {})
    }).then(function(r) { return r.json(); });
}

function __fmtPct(n) {
    const v = typeof n === 'number' && Number.isFinite(n) ? n : 0;
    return (Math.round(v * 10) / 10).toFixed(1);
}

function __fmtInt(n) {
    const v = typeof n === 'number' && Number.isFinite(n) ? n : 0;
    return String(Math.round(v));
}

window.loadProcessList = function() {
    const container = __setContainerHtml('processListContainer', __loadingHtml('加载中...'));
    fetch('/api/process/list', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!container) return;
            const processes = payload && Array.isArray(payload.processes) ? payload.processes : [];
            const stats = payload && payload.stats ? payload.stats : {};
            if (!processes.length) {
                container.innerHTML = __emptyHtml('暂无进程数据');
                return;
            }

            const cpuPct = typeof stats.cpu_percent === 'number' ? stats.cpu_percent : null;
            const memUsed = typeof stats.memory_used === 'number' ? stats.memory_used : null;
            const memTotal = typeof stats.memory_total === 'number' ? stats.memory_total : null;
            const memPct = typeof stats.memory_percent === 'number' ? stats.memory_percent : null;
            const procCount = typeof stats.process_count === 'number' ? stats.process_count : processes.length;

            const header = '<div style="padding:14px 16px;border-bottom:1px solid #eee;background:#f6f8fa;">'
                + '<div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;">'
                + '<div style="font-weight:600;">总进程：' + escapeHtml(String(procCount)) + '</div>'
                + '<div style="display:flex;gap:10px;flex-wrap:wrap;font-size:12px;color:#57606a;">'
                + '<span>CPU：' + (cpuPct === null ? '-' : escapeHtml(__fmtPct(cpuPct)) + '%') + '</span>'
                + '<span>内存：' + (memUsed === null || memTotal === null ? '-' : escapeHtml(formatSize(memUsed)) + ' / ' + escapeHtml(formatSize(memTotal)) + (memPct === null ? '' : ' (' + escapeHtml(__fmtPct(memPct)) + '%)')) + '</span>'
                + '</div>'
                + '</div>'
                + '</div>';

            const rows = processes.map(function(p) {
                const pid = p.pid;
                const cpu = typeof p.cpu_percent === 'number' ? p.cpu_percent : 0;
                const mem = typeof p.memory_percent === 'number' ? p.memory_percent : 0;
                const rss = typeof p.memory_rss === 'number' ? p.memory_rss : 0;
                const user = p.user || '-';
                const cmd = p.command || p.full_command || '-';
                const elapsed = p.elapsed || '-';
                const safePid = escapeHtml(String(pid));
                return '<div style="padding:12px 16px;border-bottom:1px solid #eee;">'
                    + '<div style="display:flex;gap:12px;align-items:flex-start;justify-content:space-between;">'
                    + '<div style="min-width:0;">'
                    + '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(String(cmd)) + '</div>'
                    + '<div style="margin-top:4px;font-size:12px;color:#57606a;display:flex;gap:10px;flex-wrap:wrap;">'
                    + '<span>PID ' + safePid + '</span>'
                    + '<span>' + escapeHtml(String(user)) + '</span>'
                    + '<span>CPU ' + escapeHtml(__fmtPct(cpu)) + '%</span>'
                    + '<span>MEM ' + escapeHtml(__fmtPct(mem)) + '%</span>'
                    + '<span>' + escapeHtml(formatSize(rss)) + '</span>'
                    + '<span>' + escapeHtml(String(elapsed)) + '</span>'
                    + '</div>'
                    + '</div>'
                    + '<div style="display:flex;gap:8px;flex-shrink:0;">'
                    + '<button type="button" data-action="proc-detail" data-pid="' + safePid + '" style="border:1px solid #d0d7de;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;">详情</button>'
                    + '<button type="button" data-action="proc-kill" data-pid="' + safePid + '" style="border:1px solid #cf222e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#cf222e;">结束</button>'
                    + '</div>'
                    + '</div>'
                    + '</div>';
            }).join('');

            container.innerHTML = header + rows;

            Array.from(container.querySelectorAll('button[data-action="proc-detail"]')).forEach(function(btn) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const pid = parseInt(btn.getAttribute('data-pid') || '0', 10);
                    if (!pid) return;
                    window.openProcessDetailModal(pid);
                });
            });

            Array.from(container.querySelectorAll('button[data-action="proc-kill"]')).forEach(function(btn) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const pid = parseInt(btn.getAttribute('data-pid') || '0', 10);
                    if (!pid) return;
                    const ok = window.confirm('确认结束进程 PID ' + String(pid) + ' ?');
                    if (!ok) return;
                    fetch('/api/process/kill/' + encodeURIComponent(String(pid)), { method: 'POST', headers: authHeaders() })
                        .then(function(r) { return r.json(); })
                        .then(function(data) {
                            const payload = apiData(data);
                            if (payload && payload.message && typeof window.showToast === 'function') window.showToast(payload.message, 'success');
                            window.loadProcessList();
                        })
                        .catch(function() {
                            if (typeof window.showToast === 'function') window.showToast('结束失败', 'error');
                        });
                });
            });
        })
        .catch(function() {
            if (container) container.innerHTML = __errorHtml('加载失败');
        });
};

window.openProcessDetailModal = function(pid) {
    Drawer.open('processDetailModal');
    const container = __setContainerHtml('processDetailContent', __loadingHtml('加载中...'));
    fetch('/api/process/ports/' + encodeURIComponent(String(pid)), { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!container) return;
            const ports = payload && Array.isArray(payload.ports) ? payload.ports : [];
            const rows = ports.length
                ? ports.map(function(p) {
                    return '<div style="padding:10px 12px;border:1px solid #d0d7de;border-radius:8px;background:#fff;display:flex;justify-content:space-between;gap:10px;">'
                        + '<div style="font-weight:600;">' + escapeHtml(String(p.protocol || '-')) + ' ' + escapeHtml(String(p.port || '-')) + '</div>'
                        + '<div style="font-size:12px;color:#57606a;text-align:right;">' + escapeHtml(String(p.state || '-')) + (p.program ? ' · ' + escapeHtml(String(p.program)) : '') + '</div>'
                        + '</div>';
                }).join('<div style="height:8px;"></div>')
                : __emptyHtml('未发现监听端口');

            container.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
                + '<div style="font-weight:600;">PID ' + escapeHtml(String(pid)) + '</div>'
                + '<div style="display:flex;gap:8px;">'
                + '<button type="button" id="procDetailRefreshBtn" style="border:1px solid #d0d7de;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;">刷新</button>'
                + '<button type="button" id="procDetailKillBtn" style="border:1px solid #cf222e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#cf222e;">结束</button>'
                + '</div>'
                + '</div>'
                + rows;

            const refreshBtn = document.getElementById('procDetailRefreshBtn');
            if (refreshBtn) refreshBtn.addEventListener('click', function() { window.openProcessDetailModal(pid); });
            const killBtn = document.getElementById('procDetailKillBtn');
            if (killBtn) killBtn.addEventListener('click', function() {
                const ok = window.confirm('确认结束进程 PID ' + String(pid) + ' ?');
                if (!ok) return;
                fetch('/api/process/kill/' + encodeURIComponent(String(pid)), { method: 'POST', headers: authHeaders() })
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        const payload = apiData(data);
                        if (payload && payload.message && typeof window.showToast === 'function') window.showToast(payload.message, 'success');
                        Drawer.close('processDetailModal');
                        window.loadProcessList();
                    })
                    .catch(function() {
                        if (typeof window.showToast === 'function') window.showToast('结束失败', 'error');
                    });
            });
        })
        .catch(function() {
            if (container) container.innerHTML = __errorHtml('加载失败');
        });
};

window.loadSystemPackageList = function() {
    const container = __setContainerHtml('systemPackageListContainer', __loadingHtml('加载中...'));
    fetch('/api/system-packages/list', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!container) return;
            const packages = payload && Array.isArray(payload.packages) ? payload.packages : [];
            if (!packages.length) {
                container.innerHTML = __emptyHtml('暂无系统包数据');
                return;
            }
            container.innerHTML = '<div style="display:flex;flex-direction:column;gap:10px;">' + packages.map(function(p) {
                const name = p.name || '-';
                const version = p.version || '';
                const manager = p.manager || '';
                return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;display:flex;justify-content:space-between;gap:12px;align-items:center;">'
                    + '<div style="min-width:0;">'
                    + '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(String(name)) + '</div>'
                    + '<div style="font-size:12px;color:#57606a;margin-top:2px;">' + escapeHtml(String(version)) + (manager ? ' · ' + escapeHtml(String(manager)) : '') + '</div>'
                    + '</div>'
                    + '<button type="button" data-action="sys-pkg-uninstall" data-name="' + escapeHtml(String(name)) + '" data-manager="' + escapeHtml(String(manager)) + '" style="border:1px solid #cf222e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#cf222e;flex-shrink:0;">卸载</button>'
                    + '</div>';
            }).join('') + '</div>';

            Array.from(container.querySelectorAll('button[data-action="sys-pkg-uninstall"]')).forEach(function(btn) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const name = btn.getAttribute('data-name') || '';
                    const manager = btn.getAttribute('data-manager') || '';
                    if (!name) return;
                    const ok = window.confirm('确认卸载 ' + name + ' ?');
                    if (!ok) return;
                    __postJson('/api/system-packages/uninstall', { name: name, manager: manager })
                        .then(function(data) {
                            const payload = apiData(data);
                            const msg = payload && payload.message ? payload.message : '已提交';
                            if (typeof window.showToast === 'function') window.showToast(msg, 'success');
                            window.loadSystemPackageList();
                        })
                        .catch(function() {
                            if (typeof window.showToast === 'function') window.showToast('卸载失败', 'error');
                        });
                });
            });
        })
        .catch(function() {
            if (container) container.innerHTML = __errorHtml('加载失败（可能不支持此系统）');
        });
};

function __renderPkgList(containerId, opts) {
    const options = opts || {};
    const title = options.title || '';
    const listUrl = options.listUrl || '';
    const installUrl = options.installUrl || '';
    const uninstallUrl = options.uninstallUrl || '';
    const container = __setContainerHtml(containerId, __loadingHtml('加载中...'));
    fetch(listUrl, { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!container) return;
            const packages = payload && Array.isArray(payload.packages) ? payload.packages : [];

            const header = '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px;">'
                + '<input id="' + escapeHtml(containerId) + '_installInput" type="text" placeholder="输入包名，例如 ' + escapeHtml(title) + '" style="flex:1;min-width:180px;padding:10px 12px;border:1px solid #d0d7de;border-radius:10px;font-size:14px;">'
                + '<button type="button" id="' + escapeHtml(containerId) + '_installBtn" style="border:1px solid #0969da;background:#0969da;color:#fff;border-radius:10px;padding:10px 14px;cursor:pointer;">安装</button>'
                + '</div>';

            if (!packages.length) {
                container.innerHTML = header + __emptyHtml('暂无已安装包');
            } else {
                const rows = '<div style="display:flex;flex-direction:column;gap:10px;">' + packages.map(function(p) {
                    const name = p.name || '-';
                    const version = p.version || '';
                    return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;display:flex;justify-content:space-between;gap:12px;align-items:center;">'
                        + '<div style="min-width:0;">'
                        + '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(String(name)) + '</div>'
                        + '<div style="font-size:12px;color:#57606a;margin-top:2px;">' + escapeHtml(String(version)) + '</div>'
                        + '</div>'
                        + '<button type="button" data-action="pkg-uninstall" data-name="' + escapeHtml(String(name)) + '" style="border:1px solid #cf222e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#cf222e;flex-shrink:0;">卸载</button>'
                        + '</div>';
                }).join('') + '</div>';
                container.innerHTML = header + rows;
            }

            const inputEl = document.getElementById(containerId + '_installInput');
            const installBtn = document.getElementById(containerId + '_installBtn');
            if (installBtn) {
                installBtn.addEventListener('click', function() {
                    const pkg = inputEl ? (inputEl.value || '').trim() : '';
                    if (!pkg) return;
                    installBtn.disabled = true;
                    installBtn.textContent = '安装中...';
                    __postJson(installUrl, { package: pkg })
                        .then(function(data) {
                            const payload = apiData(data);
                            const msg = payload && payload.message ? payload.message : '已提交';
                            if (typeof window.showToast === 'function') window.showToast(msg, 'success');
                            __renderPkgList(containerId, options);
                        })
                        .catch(function() {
                            if (typeof window.showToast === 'function') window.showToast('安装失败', 'error');
                        })
                        .finally(function() {
                            installBtn.disabled = false;
                            installBtn.textContent = '安装';
                        });
                });
            }

            Array.from(container.querySelectorAll('button[data-action="pkg-uninstall"]')).forEach(function(btn) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const name = btn.getAttribute('data-name') || '';
                    if (!name) return;
                    const ok = window.confirm('确认卸载 ' + name + ' ?');
                    if (!ok) return;
                    __postJson(uninstallUrl, { package: name })
                        .then(function(data) {
                            const payload = apiData(data);
                            const msg = payload && payload.message ? payload.message : '已提交';
                            if (typeof window.showToast === 'function') window.showToast(msg, 'success');
                            __renderPkgList(containerId, options);
                        })
                        .catch(function() {
                            if (typeof window.showToast === 'function') window.showToast('卸载失败', 'error');
                        });
                });
            });
        })
        .catch(function() {
            if (container) container.innerHTML = __errorHtml('加载失败');
        });
}

window.loadPipList = function() {
    __renderPkgList('pipListContainer', {
        title: 'requests',
        listUrl: '/api/pip/list',
        installUrl: '/api/pip/install',
        uninstallUrl: '/api/pip/uninstall'
    });
};

window.loadNpmList = function() {
    __renderPkgList('npmListContainer', {
        title: 'eslint',
        listUrl: '/api/npm/list',
        installUrl: '/api/npm/install',
        uninstallUrl: '/api/npm/uninstall'
    });
};

window.loadDockerTabs = function(tab) {
    const t = (tab || 'images') === 'containers' ? 'containers' : 'images';
    const imagesEl = document.getElementById('dockerImagesContainer');
    const containersEl = document.getElementById('dockerContainersContainer');
    const tabs = Array.from(document.querySelectorAll('#dockerModal .docker-tab'));
    tabs.forEach(function(btn) {
        const isActive = (btn.getAttribute('data-tab') || '') === t;
        if (isActive) btn.classList.add('active');
        else btn.classList.remove('active');
        btn.style.borderBottomColor = isActive ? '#0969da' : 'transparent';
        btn.style.color = isActive ? '#0969da' : '#24292f';
        btn.style.fontWeight = isActive ? '600' : '400';
    });
    if (imagesEl) imagesEl.style.display = t === 'images' ? 'block' : 'none';
    if (containersEl) containersEl.style.display = t === 'containers' ? 'block' : 'none';

    if (t === 'images') {
        if (imagesEl) imagesEl.innerHTML = __loadingHtml('加载镜像...');
        fetch('/api/docker/images', { headers: authHeaders() })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                const payload = apiData(data);
                if (!imagesEl) return;
                const images = payload && Array.isArray(payload.images) ? payload.images : [];
                if (!images.length) {
                    imagesEl.innerHTML = __emptyHtml('暂无镜像');
                    return;
                }
                imagesEl.innerHTML = '<div style="display:flex;flex-direction:column;gap:10px;">' + images.map(function(img) {
                    const repo = img.repository || '-';
                    const tag = img.tag || '';
                    const id = img.id || '';
                    const size = img.size || '';
                    const created = img.created || '';
                    return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;display:flex;justify-content:space-between;gap:12px;align-items:center;">'
                        + '<div style="min-width:0;">'
                        + '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(String(repo)) + (tag ? ':' + escapeHtml(String(tag)) : '') + '</div>'
                        + '<div style="font-size:12px;color:#57606a;margin-top:2px;">' + escapeHtml(String(id)) + (size ? ' · ' + escapeHtml(String(size)) : '') + (created ? ' · ' + escapeHtml(String(created)) : '') + '</div>'
                        + '</div>'
                        + '<button type="button" data-action="docker-img-rm" data-id="' + escapeHtml(String(id)) + '" style="border:1px solid #cf222e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#cf222e;flex-shrink:0;">删除</button>'
                        + '</div>';
                }).join('') + '</div>';

                Array.from(imagesEl.querySelectorAll('button[data-action="docker-img-rm"]')).forEach(function(btn) {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        const id = btn.getAttribute('data-id') || '';
                        if (!id) return;
                        const ok = window.confirm('确认删除镜像 ' + id + ' ?');
                        if (!ok) return;
                        __postJson('/api/docker/image/rm', { id: id })
                            .then(function(data) {
                                const payload = apiData(data);
                                const msg = payload && payload.message ? payload.message : '已提交';
                                if (typeof window.showToast === 'function') window.showToast(msg, 'success');
                                window.loadDockerTabs('images');
                            })
                            .catch(function() {
                                if (typeof window.showToast === 'function') window.showToast('删除失败', 'error');
                            });
                    });
                });
            })
            .catch(function() {
                if (imagesEl) imagesEl.innerHTML = __errorHtml('加载失败（Docker 可能未安装）');
            });
    } else {
        if (containersEl) containersEl.innerHTML = __loadingHtml('加载容器...');
        fetch('/api/docker/containers', { headers: authHeaders() })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                const payload = apiData(data);
                if (!containersEl) return;
                const containers = payload && Array.isArray(payload.containers) ? payload.containers : [];
                if (!containers.length) {
                    containersEl.innerHTML = __emptyHtml('暂无容器');
                    return;
                }
                containersEl.innerHTML = '<div style="display:flex;flex-direction:column;gap:10px;">' + containers.map(function(c) {
                    const id = c.id || '';
                    const name = c.name || '';
                    const image = c.image || '';
                    const status = c.status || '';
                    const ports = c.ports || '';
                    const running = status.toLowerCase().indexOf('up') >= 0;
                    const actionText = running ? '停止' : '启动';
                    const actionType = running ? 'stop' : 'start';
                    return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">'
                        + '<div style="min-width:0;">'
                        + '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(String(name || id)) + '</div>'
                        + '<div style="font-size:12px;color:#57606a;margin-top:2px;word-break:break-all;">' + escapeHtml(String(image)) + '</div>'
                        + '<div style="font-size:12px;color:#57606a;margin-top:2px;word-break:break-all;">' + escapeHtml(String(status)) + (ports ? ' · ' + escapeHtml(String(ports)) : '') + '</div>'
                        + '</div>'
                        + '<div style="display:flex;gap:8px;flex-shrink:0;">'
                        + '<button type="button" data-action="docker-ctr-act" data-id="' + escapeHtml(String(id)) + '" data-op="' + escapeHtml(String(actionType)) + '" style="border:1px solid #0969da;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#0969da;">' + escapeHtml(String(actionText)) + '</button>'
                        + '<button type="button" data-action="docker-ctr-rm" data-id="' + escapeHtml(String(id)) + '" style="border:1px solid #cf222e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#cf222e;">删除</button>'
                        + '</div>'
                        + '</div>';
                }).join('') + '</div>';

                Array.from(containersEl.querySelectorAll('button[data-action="docker-ctr-act"]')).forEach(function(btn) {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        const id = btn.getAttribute('data-id') || '';
                        const op = btn.getAttribute('data-op') || '';
                        if (!id || !op) return;
                        const url = op === 'stop' ? '/api/docker/container/stop' : '/api/docker/container/start';
                        __postJson(url, { id: id })
                            .then(function(data) {
                                const payload = apiData(data);
                                const msg = payload && payload.message ? payload.message : '已提交';
                                if (typeof window.showToast === 'function') window.showToast(msg, 'success');
                                window.loadDockerTabs('containers');
                            })
                            .catch(function() {
                                if (typeof window.showToast === 'function') window.showToast('操作失败', 'error');
                            });
                    });
                });

                Array.from(containersEl.querySelectorAll('button[data-action="docker-ctr-rm"]')).forEach(function(btn) {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        const id = btn.getAttribute('data-id') || '';
                        if (!id) return;
                        const ok = window.confirm('确认删除容器 ' + id + ' ?');
                        if (!ok) return;
                        __postJson('/api/docker/container/rm', { id: id, force: true })
                            .then(function(data) {
                                const payload = apiData(data);
                                const msg = payload && payload.message ? payload.message : '已提交';
                                if (typeof window.showToast === 'function') window.showToast(msg, 'success');
                                window.loadDockerTabs('containers');
                            })
                            .catch(function() {
                                if (typeof window.showToast === 'function') window.showToast('删除失败', 'error');
                            });
                    });
                });
            })
            .catch(function() {
                if (containersEl) containersEl.innerHTML = __errorHtml('加载失败（Docker 可能未安装）');
            });
    }
};

function __systemdControl(service, action, scope) {
    const svc = String(service || '');
    const act = String(action || '');
    const scp = scope || 'user';
    if (!svc || !act) return;
    if (typeof window.showTaskListener === 'function') window.showTaskListener('正在执行 ' + act + ' …');
    __postJson('/api/systemd/control', { service: svc, action: act, scope: scp })
        .then(function(data) {
            const payload = apiData(data);
            const taskId = payload && payload.taskId ? payload.taskId : null;
            if (!taskId || !window.TaskPoller || typeof window.TaskPoller.start !== 'function') {
                if (typeof window.hideTaskListener === 'function') window.hideTaskListener();
                window.loadSystemdList();
                return;
            }
            if (window.__activeTaskPoller && typeof window.__activeTaskPoller.cancel === 'function') {
                window.__activeTaskPoller.cancel();
                window.__activeTaskPoller = null;
            }
            window.__activeTaskPoller = window.TaskPoller.start(taskId, {
                intervalMs: 900,
                timeoutMs: 30 * 1000,
                onUpdate: function(evt) {
                    if (!evt) return;
                    const st = evt.status;
                    if (typeof window.showTaskListener === 'function') window.showTaskListener('systemd ' + act + '：' + (st || 'running') + ' …');
                }
            });
            window.__activeTaskPoller.promise.then(function(res) {
                window.__activeTaskPoller = null;
                if (typeof window.hideTaskListener === 'function') window.hideTaskListener();
                if (!res || !res.ok) {
                    if (typeof window.showToast === 'function') window.showToast('操作失败', 'error');
                    window.loadSystemdList();
                    return;
                }
                if (typeof window.showToast === 'function') window.showToast('操作完成', 'success');
                window.loadSystemdList();
            });
        })
        .catch(function() {
            if (typeof window.hideTaskListener === 'function') window.hideTaskListener();
            if (typeof window.showToast === 'function') window.showToast('操作失败', 'error');
        });
}

window.loadSystemdList = function() {
    const container = __setContainerHtml('systemdListContainer', __loadingHtml('加载中...'));
    
    // 先获取 user 和 system 两个列表
    Promise.all([
        fetch('/api/systemd/list?scope=user', { headers: authHeaders() }).then(r => r.json()),
        fetch('/api/systemd/list?scope=system', { headers: authHeaders() }).then(r => r.json())
    ]).then(function(results) {
        if (!container) return;
        
        const userData = apiData(results[0]) || { services: [] };
        const systemData = apiData(results[1]) || { services: [] };
        
        const userServices = Array.isArray(userData.services) ? userData.services : [];
        const systemServices = Array.isArray(systemData.services) ? systemData.services : [];
        
        // 更新计数
        document.getElementById('systemdUserCount').textContent = userServices.length;
        document.getElementById('systemdSystemCount').textContent = systemServices.length;
        
        // 保存数据到全局
        window._systemdData = {
            user: userServices,
            system: systemServices
        };
        
        // 默认显示 user
        switchSystemdTab('user');
    }).catch(function() {
        if (container) container.innerHTML = __errorHtml('加载失败（可能不支持此系统）');
    });
};

// Tab 切换
window.switchSystemdTab = function(scope) {
    // 保存当前 scope 到全局
    window._systemdCurrentScope = scope;
    
    // 更新 Tab 样式
    document.getElementById('systemdTabUser').style.background = scope === 'user' ? '#fff' : '#f6f8fa';
    document.getElementById('systemdTabUser').style.borderColor = scope === 'user' ? '#0969da' : '#d0d7de';
    document.getElementById('systemdTabSystem').style.background = scope === 'system' ? '#fff' : '#f6f8fa';
    document.getElementById('systemdTabSystem').style.borderColor = scope === 'system' ? '#0969da' : '#d0d7de';
    
    // 获取搜索关键词
    const searchInput = document.getElementById('systemdSearch');
    const keyword = (searchInput?.value || '').toLowerCase();
    
    // 过滤并渲染
    const data = window._systemdData || { user: [], system: [] };
    const services = scope === 'user' ? data.user : data.system;
    const filtered = keyword ? services.filter(s => s.name.toLowerCase().includes(keyword)) : services;
    
    const container = document.getElementById('systemdListContainer');
    if (!container) return;
    
    if (!filtered.length) {
        container.innerHTML = __emptyHtml(keyword ? '未找到匹配的服务' : '暂无服务');
        return;
    }
    
    // 排序
    filtered.sort(function(a, b) {
        if (a.enabled && !b.enabled) return -1;
        if (!a.enabled && b.enabled) return 1;
        const timeA = a.active_since ? new Date(a.active_since).getTime() : 0;
        const timeB = b.active_since ? new Date(b.active_since).getTime() : 0;
        return timeB - timeA;
    });
    
    function formatSinceAgo(iso) {
        if (!iso) return '';
        var ts = Date.parse(String(iso));
        if (!Number.isFinite(ts)) return '';
        var diffMs = Date.now() - ts;
        if (!Number.isFinite(diffMs) || diffMs < 0) return '';
        var sec = Math.floor(diffMs / 1000);
        if (sec < 10) return '刚刚';
        if (sec < 60) return sec + 's ago';
        var min = Math.floor(sec / 60);
        if (min < 60) return min + 'm ago';
        var hr = Math.floor(min / 60);
        if (hr < 24) return hr + 'h ago';
        var day = Math.floor(hr / 24);
        return day + 'd ago';
    }
    
    container.innerHTML = '<div style="display:flex;flex-direction:column;gap:10px;">' + filtered.map(function(s) {
        const name = s.name || '-';
        const desc = s.description || '';
        const active = s.active || '';
        const sub = s.sub || '';
        const sinceAgo = formatSinceAgo(s.active_since);
        const enabled = !!s.enabled;
        const isActive = String(active).toLowerCase() === 'active';
        const badgeColor = isActive ? '#2da44e' : '#cf222e';
        const badgeText = isActive ? 'active' : (active || 'inactive');
        return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;">'
            + '<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">'
            + '<div style="min-width:0;">'
            + '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">'
            + '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(String(name)) + '</div>'
            + '<span style="font-size:11px;padding:2px 8px;border-radius:999px;background:' + badgeColor + ';color:#fff;">' + escapeHtml(String(badgeText)) + '</span>'
            + (enabled ? '<span style="font-size:11px;padding:2px 8px;border-radius:999px;background:#ddf4ff;color:#0969da;">enabled</span>' : '')
            + '</div>'
            + (desc ? '<div style="font-size:12px;color:#57606a;margin-top:2px;word-break:break-word;">' + escapeHtml(String(desc)) + '</div>' : '')
            + '<div style="font-size:12px;color:#57606a;margin-top:2px;">' + escapeHtml(String(active)) + (sub ? ' (' + escapeHtml(String(sub)) + ')' : '') + '</div>'
            + (sinceAgo ? '<div style="font-size:12px;color:#57606a;margin-top:2px;">启动于 ' + escapeHtml(String(sinceAgo)) + '</div>' : '')
            + '</div>'
            + '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:4px;flex-shrink:0;width:80px;">'
            + '<button type="button" onclick="openServiceLog(\'' + escapeHtml(String(name)) + '\')" style="border:1px solid #8250df;background:#fff;border-radius:4px;padding:4px;cursor:pointer;color:#8250df;" title="日志">📋</button>'
            + '<button type="button" data-action="systemd" data-op="restart" data-name="' + escapeHtml(String(name)) + '" style="border:1px solid #0969da;background:#fff;border-radius:4px;padding:4px;cursor:pointer;color:#0969da;" title="重启">🔄</button>'
            + '<button type="button" data-action="systemd" data-op="start" data-name="' + escapeHtml(String(name)) + '" style="border:1px solid #2da44e;background:#fff;border-radius:4px;padding:4px;cursor:pointer;color:#2da44e;" title="启动">▶</button>'
            + '<button type="button" data-action="systemd" data-op="stop" data-name="' + escapeHtml(String(name)) + '" style="border:1px solid #cf222e;background:#fff;border-radius:4px;padding:4px;cursor:pointer;color:#cf222e;" title="停止">⏹</button>'
            + '</div>'
            + '</div>'
            + '</div>';
    }).join('') + '</div>';

    Array.from(container.querySelectorAll('button[data-action="systemd"]')).forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const op = btn.getAttribute('data-op') || '';
            const name = btn.getAttribute('data-name') || '';
            if (!op || !name) return;
            // 获取当前 scope
            const scope = document.getElementById('systemdTabUser').style.background === 'rgb(255, 255, 255)' ? 'user' : 'system';
            __systemdControl(name, op, scope);
        });
    });
};

// 搜索过滤
window.filterSystemdServices = function() {
    const scope = document.getElementById('systemdTabUser').style.background === 'rgb(255, 255, 255)' ? 'user' : 'system';
    switchSystemdTab(scope);
};

window.loadDiskList = function() {
    const container = __setContainerHtml('diskListContainer', __loadingHtml('加载中...'));
    fetch('/api/disk/list', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!container) return;
            const disks = payload && Array.isArray(payload.disks) ? payload.disks : [];
            if (!disks.length) {
                container.innerHTML = __emptyHtml('暂无磁盘数据');
                return;
            }
            container.innerHTML = '<div style="display:flex;flex-direction:column;gap:10px;">' + disks.map(function(d) {
                const dev = d.device || '-';
                const total = d.total || '-';
                const used = d.used || '-';
                const avail = d.available || '-';
                const pct = d.use_percent || '-';
                const mp = d.mountpoint || '-';
                const fs = d.fstype || '';
                return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;">'
                    + '<div style="font-weight:600;word-break:break-all;">' + escapeHtml(String(dev)) + '</div>'
                    + '<div style="font-size:12px;color:#57606a;margin-top:2px;word-break:break-all;">挂载：' + escapeHtml(String(mp)) + (fs ? ' · ' + escapeHtml(String(fs)) : '') + '</div>'
                    + '<div style="display:flex;gap:10px;flex-wrap:wrap;font-size:12px;color:#57606a;margin-top:6px;">'
                    + '<span>已用 ' + escapeHtml(String(used)) + '</span>'
                    + '<span>可用 ' + escapeHtml(String(avail)) + '</span>'
                    + '<span>总量 ' + escapeHtml(String(total)) + '</span>'
                    + '<span>使用率 ' + escapeHtml(String(pct)) + '%</span>'
                    + '</div>'
                    + '</div>';
            }).join('') + '</div>';
        })
        .catch(function() {
            if (container) container.innerHTML = __errorHtml('加载失败（可能不支持此系统）');
        });
};

window.loadNetworkList = function() {
    const container = __setContainerHtml('networkListContainer', __loadingHtml('加载中...'));
    fetch('/api/network/list', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!container) return;
            const interfaces = payload && Array.isArray(payload.interfaces) ? payload.interfaces : [];
            if (!interfaces.length) {
                container.innerHTML = __emptyHtml('暂无网络信息');
                return;
            }
            container.innerHTML = '<div style="display:flex;flex-direction:column;gap:10px;">' + interfaces.map(function(n) {
                const name = n.name || '-';
                const state = n.state || '-';
                const ipv4 = n.ipv4 || '';
                const ipv6 = n.ipv6 || '';
                const mac = n.mac || '';
                const mtu = n.mtu || '';
                const bc = n.broadcast || '';
                const up = String(state).toUpperCase() === 'UP';
                const badgeColor = up ? '#2da44e' : '#cf222e';
                return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;">'
                    + '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">'
                    + '<div style="font-weight:600;">' + escapeHtml(String(name)) + '</div>'
                    + '<span style="font-size:11px;padding:2px 8px;border-radius:999px;background:' + badgeColor + ';color:#fff;">' + escapeHtml(String(state)) + '</span>'
                    + (mtu ? '<span style="font-size:11px;padding:2px 8px;border-radius:999px;background:#f6f8fa;color:#57606a;">MTU ' + escapeHtml(String(mtu)) + '</span>' : '')
                    + '</div>'
                    + '<div style="font-size:12px;color:#57606a;margin-top:6px;display:flex;flex-direction:column;gap:4px;">'
                    + (ipv4 ? '<div>IPv4：' + escapeHtml(String(ipv4)) + '</div>' : '')
                    + (ipv6 ? '<div>IPv6：' + escapeHtml(String(ipv6)) + '</div>' : '')
                    + (mac ? '<div>MAC：' + escapeHtml(String(mac)) + '</div>' : '')
                    + (bc ? '<div>Broadcast：' + escapeHtml(String(bc)) + '</div>' : '')
                    + '</div>'
                    + '</div>';
            }).join('') + '</div>';
        })
        .catch(function() {
            if (container) container.innerHTML = __errorHtml('加载失败（可能不支持此系统）');
        });
};

window.openProcessModal = function() { Drawer.open('processModal'); loadProcessList(); };
window.openSystemPackageModal = function() { Drawer.open('systemPackageModal'); loadSystemPackageList(); };
window.openPipModal = function() { Drawer.open('pipModal'); loadPipList(); };
window.openNpmModal = function() { Drawer.open('npmModal'); loadNpmList(); };
window.openDockerModal = function() { Drawer.open('dockerModal'); loadDockerTabs(); };
window.openSystemdModal = function() { Drawer.open('systemdModal'); loadSystemdList(); };
window.openDiskModal = function() { Drawer.open('diskModal'); loadDiskList(); };

// 打开服务日志
window.openServiceLog = function(serviceName) {
    const scope = window._systemdCurrentScope || 'user';
    const url = '/log/viewer?service=' + encodeURIComponent(serviceName) + '&scope=' + scope;
    window.open(url, '_blank');
};

// GPU显卡信息
window.loadGpuInfo = function() {
    const container = document.getElementById('gpuInfoContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    
    fetch('/api/gpu/info', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (!payload || !container) return;
            
            const gpu = payload.gpu || {};
            const processes = payload.processes || [];
            
            // 计算颜色
            const tempColor = gpu.temperature > 70 ? '#cf222e' : gpu.temperature > 50 ? '#d29922' : '#24292f';
            const memPercent = gpu.memory_used / gpu.memory_total * 100;
            const memColor = memPercent > 80 ? '#cf222e' : memPercent > 50 ? '#d29922' : '#2da44e';
            const powerPercent = gpu.power_total > 0 ? gpu.power_used / gpu.power_total * 100 : 0;
            const powerColor = powerPercent > 80 ? '#cf222e' : powerPercent > 50 ? '#d29922' : '#2da44e';
            const utilColor = gpu.utilization > 80 ? '#cf222e' : gpu.utilization > 50 ? '#d29922' : '#2da44e';
            
            let html = '';
            
            // ========== GPU标题卡片 ==========
            html += '<div style="background:linear-gradient(135deg, #1a7f37 0%, #2da44e 100%);color:#fff;padding:16px;border-radius:12px;margin-bottom:16px;">';
            html += '<div style="font-size:18px;font-weight:600;margin-bottom:4px;">' + escapeHtml(gpu.name || 'Unknown GPU') + '</div>';
            html += '<div style="font-size:12px;opacity:0.9;">驱动 ' + escapeHtml(gpu.driver || '-') + ' | CUDA ' + escapeHtml(gpu.cuda || '-') + '</div>';
            html += '</div>';
            
            // ========== 状态指标卡片 ==========
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">状态</div>';
            html += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;">';
            
            // 温度
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center;">';
            html += '<div style="font-size:22px;font-weight:600;color:' + tempColor + ';">' + (gpu.temperature || 0) + '°</div>';
            html += '<div style="font-size:11px;color:#666;margin-top:2px;">温度</div>';
            html += '</div>';
            
            // 风扇
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center;">';
            html += '<div style="font-size:22px;font-weight:600;color:' + utilColor + ';">' + (gpu.fan_percent || 0) + '%</div>';
            html += '<div style="font-size:11px;color:#666;margin-top:2px;">风扇</div>';
            html += '</div>';
            
            // 利用率
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center;">';
            html += '<div style="font-size:22px;font-weight:600;color:' + utilColor + ';">' + (gpu.utilization || 0) + '%</div>';
            html += '<div style="font-size:11px;color:#666;margin-top:2px;">GPU</div>';
            html += '</div>';
            
            html += '</div></div>';
            
            // ========== 显存卡片 ==========
            const memPercentDisplay = Math.round(memPercent * 10) / 10;
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">显存</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;">';
            html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">';
            html += '<span style="font-size:14px;font-weight:500;">' + (gpu.memory_used || 0) + ' / ' + (gpu.memory_total || 1) + ' MiB</span>';
            html += '<span style="font-size:13px;color:' + memColor + ';">' + memPercentDisplay + '%</span>';
            html += '</div>';
            html += '<div style="height:8px;background:#e1e4e8;border-radius:4px;overflow:hidden;">';
            html += '<div style="width:' + memPercent + '%;height:100%;background:' + memColor + ';transition:width 0.3s;"></div>';
            html += '</div>';
            html += '</div></div>';
            
            // ========== 功耗卡片 ==========
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">功耗</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;">';
            html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">';
            html += '<span style="font-size:14px;font-weight:500;">' + (gpu.power_used || 0) + ' / ' + (gpu.power_total || 0) + ' W</span>';
            html += '<span style="font-size:13px;color:' + powerColor + ';">' + Math.round(powerPercent) + '%</span>';
            html += '</div>';
            html += '<div style="height:8px;background:#e1e4e8;border-radius:4px;overflow:hidden;">';
            html += '<div style="width:' + (powerPercent > 0 ? powerPercent : 0) + '%;height:100%;background:' + powerColor + ';transition:width 0.3s;"></div>';
            html += '</div>';
            html += '</div></div>';
            
            // ========== 进程卡片 ==========
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">进程 (' + processes.length + ')</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            
            if (processes.length === 0) {
                html += '<div style="padding:16px;text-align:center;color:#666;">无GPU进程</div>';
            } else {
                processes.forEach(function(proc, idx) {
                    const typeIcon = proc.type === 'C' ? '🧮' : proc.type === 'G' ? '🖥️' : '📦';
                    html += '<div style="padding:10px 12px;' + (idx < processes.length - 1 ? 'border-bottom:1px solid #eee;' : '') + 'display:flex;justify-content:space-between;align-items:center;">';
                    html += '<div style="display:flex;align-items:center;gap:8px;overflow:hidden;">';
                    html += '<span>' + typeIcon + '</span>';
                    html += '<span style="font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:180px;">' + escapeHtml(proc.name || 'Unknown') + '</span>';
                    html += '</div>';
                    html += '<span style="font-size:12px;color:#57606a;font-family:ui-monospace;">' + proc.memory + 'MiB</span>';
                    html += '</div>';
                });
            }
            
            html += '</div></div>';
            
            container.innerHTML = html;
        })
        .catch(function(err) {
            console.error(err);
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
                        return '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;"><div style="flex:1;min-width:0;"><div style="font-weight:500;display:flex;align-items:center;gap:8px;"><span>' + escapeHtml(name) + '</span></div><div style="font-size:12px;color:#666;margin-top:2px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;">' + (isReasoning ? '<span style="font-size:12px;background:#ddf4ff;color:#0969da;padding:2px 6px;border-radius:4px;">推理</span>' : '') + '<span>' + sizeFormatted + '</span></div></div><span style="color:#07c160;font-size:18px;">✓</span></div>';
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
    
    fetch('/api/openclaw/status', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (!payload || !container) return;
            
            let html = '';
            
            // ========== 概览卡片 ==========
            const ov = payload.overview || {};
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">概览</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">版本</span><span style="font-weight:500;font-size:14px;">' + escapeHtml(ov.version || '-') + '</span></div>';
            html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">系统</span><span style="font-size:12px;color:#57606a;max-width:200px;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + escapeHtml(ov.os || '-') + '</span></div>';
            html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">Node</span><span style="font-weight:500;font-size:14px;">' + escapeHtml(ov.node || '-') + '</span></div>';
            // 获取仪表板链接
            const dashboardUrl = 'http://' + window.location.hostname + ':18789';
            html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">仪表板</span><a href="' + escapeHtml(dashboardUrl) + '" target="_blank" style="color:#0969da;font-size:13px;">打开 ↗</a></div>';
            html += '<div style="padding:10px 12px;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">频道</span><span style="font-size:13px;">' + escapeHtml(ov.channel || '-') + '</span></div>';
            html += '</div></div>';
            
            // ========== Gateway卡片 ==========
            const gw = payload.gateway || {};
            const gwStatus = gw.service_running ? '🟢 运行中' : '🔴 已停止';
            const gwPortClass = gw.port_used ? 'color:#cf222e;' : 'color:#2da44e;';
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">Gateway</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">状态</span><span>' + gwStatus + '</span></div>';
            html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">端口</span><span style="' + gwPortClass + 'font-size:14px;">' + (gw.port || '-') + (gw.port_used ? ' (被占用)' : '') + '</span></div>';
            if (gw.latency_ms !== null) {
                html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">延迟</span><span>' + gw.latency_ms + 'ms</span></div>';
            }
            if (gw.service_pid) {
                html += '<div style="padding:10px 12px;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">PID</span><span style="font-family:ui-monospace;font-size:13px;">' + gw.service_pid + '</span></div>';
            }
            html += '</div></div>';
            
            // ========== Agents卡片 ==========
            const agents = payload.agents || [];
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">Agents (' + agents.length + ')</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            agents.forEach(function(agent, idx) {
                const statusColor = agent.status === 'pending' ? '#cf222e' : '#2da44e';
                html += '<div style="padding:10px 12px;' + (idx < agents.length - 1 ? 'border-bottom:1px solid #eee;' : '') + '">';
                html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">';
                html += '<span style="font-weight:500;font-size:14px;">' + escapeHtml(agent.name || agent.id) + '</span>';
                html += '<span style="font-size:11px;padding:1px 6px;border-radius:999px;background:#ffebe9;color:#cf222e;">' + (agent.sessions || 0) + ' 会话</span>';
                html += '</div>';
                html += '<div style="font-size:12px;color:#57606a;">' + (agent.active_ago || '-') + '</div>';
                html += '</div>';
            });
            html += '</div></div>';
            
            // ========== Channels卡片 ==========
            const channels = payload.channels || {};
            const channelNames = Object.keys(channels);
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">Channels</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            channelNames.forEach(function(ch, idx) {
                const cfg = channels[ch];
                const statusIcon = cfg.status === 'ok' ? '🟢' : (cfg.enabled ? '🟡' : '🔴');
                const statusText = cfg.status === 'ok' ? '已连接' : (cfg.enabled ? '待配置' : '已禁用');
                html += '<div style="padding:10px 12px;' + (idx < channelNames.length - 1 ? 'border-bottom:1px solid #eee;' : '') + 'display:flex;justify-content:space-between;align-items:center;">';
                html += '<div style="display:flex;align-items:center;gap:8px;">';
                html += '<span>' + statusIcon + '</span>';
                html += '<span style="font-weight:500;font-size:14px;text-transform:capitalize;">' + escapeHtml(ch) + '</span>';
                html += '</div>';
                html += '<div style="text-align:right;">';
                html += '<div style="font-size:13px;">' + statusText + '</div>';
                if (cfg.accounts_total > 0) {
                    html += '<div style="font-size:11px;color:#57606a;">' + cfg.accounts_ok + '/' + cfg.accounts_total + ' 账户</div>';
                }
                html += '</div>';
                html += '</div>';
            });
            html += '</div></div>';
            
            // ========== 诊断卡片 ==========
            const diag = payload.diagnosis || {};
            const warnings = diag.warnings || [];
            const checks = diag.checks || {};
            
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">诊断</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            
            // Warnings
            if (warnings.length > 0) {
                warnings.forEach(function(w, idx) {
                    html += '<div style="padding:10px 12px;' + (idx < warnings.length - 1 ? 'border-bottom:1px solid #eee;' : '') + 'display:flex;align-items:center;gap:8px;">';
                    html += '<span>⚠️</span>';
                    html += '<span style="font-size:13px;">' + escapeHtml(w.message) + '</span>';
                    html += '</div>';
                });
            } else {
                html += '<div style="padding:10px 12px;display:flex;align-items:center;gap:8px;color:#2da44e;">';
                html += '<span>✅</span>';
                html += '<span style="font-size:13px;">无警告</span>';
                html += '</div>';
            }
            
            // Skills check
            const skills = checks.skills || {};
            if (skills.eligible !== undefined) {
                html += '<div style="padding:10px 12px;border-top:1px solid #eee;display:flex;justify-content:space-between;align-items:center;">';
                html += '<span style="color:#666;font-size:13px;">Skills</span>';
                html += '<span>' + skills.eligible + ' 个已安装</span>';
                html += '</div>';
            }
            
            html += '</div></div>';
            
            container.innerHTML = html;
        })
        .catch(function(err) {
            console.error(err);
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败</div>';
        });
};
window.openOpenclawModal = function() { Drawer.open('openclawModal'); loadOpenclawConfig(); };

window.loadClashConfig = function() {
    const container = document.getElementById('clashContainer');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';

    fetch('/api/clash/state', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!payload) {
                container.innerHTML = __errorHtml('加载失败');
                return;
            }

            const cfg = payload.config || {};
            const svc = payload.service || {};

            const svcAvailable = !!svc.available;
            const svcName = escapeHtml(String((svc.id || 'clash.service')));
            const svcText = svcAvailable
                ? (svc.running ? '<span style="color:#2da44e;">● 运行中</span>' : '<span style="color:#cf222e;">● 未运行</span>')
                : '<span style="color:#666;">未知</span>';

            let html = '';

            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">服务状态</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            html += '<div style="padding:12px;display:flex;justify-content:space-between;align-items:center;">';
            html += '<span style="font-weight:500;">' + svcName + '</span>';
            html += '<span id="clashServiceStatus" style="font-size:12px;">' + svcText + '</span>';
            html += '</div>';
            html += '<div style="padding:0 12px 12px;display:flex;gap:8px;">';
            html += '<button onclick="clashControl(\\\'start\\\')" style="flex:1;padding:8px;border-radius:6px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:13px;">▶ 启动</button>';
            html += '<button onclick="clashControl(\\\'stop\\\')" style="flex:1;padding:8px;border-radius:6px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:13px;">⏹ 停止</button>';
            html += '<button onclick="clashControl(\\\'restart\\\')" style="flex:1;padding:8px;border-radius:6px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:13px;">🔄 重启</button>';
            html += '</div>';
            html += '</div></div>';

            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">配置文件</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;gap:8px;">';
            html += '<span style="color:#666;flex-shrink:0;">路径</span>';
            html += '<span style="font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \\\"Liberation Mono\\\", \\\"Courier New\\\", monospace;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + escapeHtml(String(cfg.path || '-')) + '</span>';
            html += '</div>';

            if (!cfg.present) {
                const msg = cfg.error ? ('读取失败：' + escapeHtml(String(cfg.error))) : '未找到配置文件';
                html += '<div style="padding:12px;color:#666;text-align:center;">' + msg + '</div>';
            } else {
                const summary = cfg.summary || {};
                const keys = Object.keys(summary);
                if (keys.length === 0) {
                    html += '<div style="padding:12px;color:#666;text-align:center;">未解析到配置摘要</div>';
                } else {
                    keys.forEach(function(k, idx) {
                        const v = summary[k];
                        const valueText = (v === null || v === undefined) ? '-' : String(v);
                        html += '<div style="padding:10px 12px;' + (idx < keys.length - 1 ? 'border-top:1px solid #eee;' : 'border-top:1px solid #eee;') + 'display:flex;justify-content:space-between;gap:8px;">';
                        html += '<span style="color:#666;flex-shrink:0;">' + escapeHtml(String(k)) + '</span>';
                        html += '<span style="text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + escapeHtml(valueText) + '</span>';
                        html += '</div>';
                    });
                }
            }
            html += '</div></div>';

            container.innerHTML = html;
        })
        .catch(function(err) {
            console.error(err);
            container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败: ' + escapeHtml(err.message) + '</div>';
        });
};

window.clashRefreshStatus = function() {
    fetch('/api/clash/state', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            const statusEl = document.getElementById('clashServiceStatus');
            if (!statusEl) return;
            if (!payload || !payload.service) {
                statusEl.innerHTML = '<span style="color:#666;">未知</span>';
                return;
            }
            const svc = payload.service || {};
            if (!svc.available) {
                statusEl.innerHTML = '<span style="color:#666;">未知</span>';
                return;
            }
            statusEl.innerHTML = svc.running
                ? '<span style="color:#2da44e;">● 运行中</span>'
                : '<span style="color:#cf222e;">● 未运行</span>';
        })
        .catch(function() {
            const statusEl = document.getElementById('clashServiceStatus');
            if (statusEl) statusEl.innerHTML = '<span style="color:#666;">未知</span>';
        });
};

window.clashControl = function(action) {
    const actions = { 'start': '启动', 'stop': '停止', 'restart': '重启' };
    if (!confirm('确定要' + actions[action] + ' Clash 服务吗？')) return;

    __postJson('/api/clash/control', { action: action })
        .then(function(data) {
            if (data && data.success) {
                alert('Clash 服务已' + actions[action]);
                window.clashRefreshStatus();
                return;
            }
            alert(actions[action] + '失败: ' + ((data && (data.message || data.error)) || '未知错误'));
        })
        .catch(function(err) { alert('请求失败: ' + err.message); });
};

window.openClashModal = function() { Drawer.open('clashModal'); };
window.closeClashModal = function() { Drawer.close('clashModal'); };

// FRP管理
window.loadFrpConfig = function() {
    const container = document.getElementById('frpContainer');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    
    fetch('/api/frp/state', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!payload) {
                container.innerHTML = __errorHtml('加载失败');
                return;
            }

            const cfg = payload.config || {};
            const svc = payload.service || {};
            const proxies = Array.isArray(cfg.proxies) ? cfg.proxies : [];

            const svcAvailable = !!svc.available;
            const svcName = escapeHtml(String((svc.id || 'frpc.service')));
            const svcText = svcAvailable
                ? (svc.running ? '<span style="color:#2da44e;">● 运行中</span>' : '<span style="color:#cf222e;">● 未运行</span>')
                : '<span style="color:#666;">未知</span>';

            const serverAddr = (cfg && cfg.serverAddr) ? String(cfg.serverAddr) : '-';
            const serverPort = (cfg && (cfg.serverPort !== null && cfg.serverPort !== undefined)) ? String(cfg.serverPort) : '-';
            const serverAddrSafe = escapeHtml(serverAddr);
            const serverPortSafe = escapeHtml(serverPort);

            let html = '';

            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">服务状态</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            html += '<div style="padding:12px;display:flex;justify-content:space-between;align-items:center;">';
            html += '<span style="font-weight:500;">' + svcName + '</span>';
            html += '<span id="frpServiceStatus" style="font-size:12px;">' + svcText + '</span>';
            html += '</div>';
            html += '<div style="padding:0 12px 12px;display:flex;gap:8px;">';
            html += '<button id="frpStartBtn" onclick="frpcControl(\'start\')" style="flex:1;padding:8px;border-radius:6px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:13px;">▶ 启动</button>';
            html += '<button id="frpStopBtn" onclick="frpcControl(\'stop\')" style="flex:1;padding:8px;border-radius:6px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:13px;">⏹ 停止</button>';
            html += '<button id="frpRestartBtn" onclick="frpcControl(\'restart\')" style="flex:1;padding:8px;border-radius:6px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:13px;">🔄 重启</button>';
            html += '</div>';
            html += '</div></div>';

            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">服务端</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;"><span style="color:#666;">地址</span><span style="font-family:monospace;">' + serverAddrSafe + '</span></div>';
            html += '<div style="padding:10px 12px;display:flex;justify-content:space-between;"><span style="color:#666;">端口</span><span>' + serverPortSafe + '</span></div>';
            html += '</div></div>';

            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;display:flex;justify-content:space-between;align-items:center;">';
            html += '<span>代理 (' + proxies.length + ')</span>';
            html += '<button onclick="openFrpProxyDrawer()" style="padding:4px 8px;border-radius:6px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:12px;">+ 添加</button>';
            html += '</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';

            if (!cfg.present) {
                const msg = cfg.error ? ('读取失败：' + escapeHtml(String(cfg.error))) : 'FRP 配置文件不存在';
                html += '<div style="padding:20px;text-align:center;color:#666;">' + msg + '</div>';
            } else if (proxies.length === 0) {
                html += '<div style="padding:20px;text-align:center;color:#666;">暂无代理</div>';
            } else {
                proxies.forEach(function(p, idx) {
                    const name = p && p.name ? String(p.name) : '-';
                    const type = p && p.type ? String(p.type) : '';
                    const localIP = p && p.localIP ? String(p.localIP) : '127.0.0.1';
                    const localPort = p && p.localPort ? String(p.localPort) : '-';
                    const remotePort = p && p.remotePort ? String(p.remotePort) : '-';
                    const localAddr = escapeHtml(localIP + ':' + localPort);
                    const remoteAddr = escapeHtml((serverAddr === '-' ? '' : serverAddr) + ':' + remotePort);
                    html += '<div style="padding:10px 12px;' + (idx < proxies.length - 1 ? 'border-bottom:1px solid #eee;' : '') + '">';
                    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">';
                    html += '<span style="font-weight:500;">' + escapeHtml(name) + '</span>';
                    html += '<span style="font-size:11px;color:#666;">' + escapeHtml(type ? type.toUpperCase() : '-') + '</span>';
                    html += '</div>';
                    html += '<div style="display:flex;justify-content:space-between;font-size:12px;color:#666;">';
                    html += '<span>本地: ' + localAddr + '</span>';
                    html += '<span>远程: ' + remoteAddr + '</span>';
                    html += '</div>';
                    html += '</div>';
                });
            }

            html += '</div></div>';

            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">配置</div>';
            html += '<div style="display:flex;gap:8px;">';
            html += '<button onclick="openFrpInEditor()" style="flex:1;padding:10px;border-radius:8px;border:1px solid #d0d7de;background:#fff;cursor:pointer;">📝 编辑配置</button>';
            html += '</div></div>';

            container.innerHTML = html;
        })
        .catch(function(err) {
            console.error(err);
            container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败: ' + err.message + '</div>';
        });
};

window.frpcRefreshStatus = function() {
    fetch('/api/frp/state', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            const statusEl = document.getElementById('frpServiceStatus');
            if (!statusEl) return;
            if (!payload || !payload.service) {
                statusEl.innerHTML = '<span style="color:#666;">未知</span>';
                return;
            }
            const svc = payload.service || {};
            if (!svc.available) {
                statusEl.innerHTML = '<span style="color:#666;">未知</span>';
                return;
            }
            statusEl.innerHTML = svc.running
                ? '<span style="color:#2da44e;">● 运行中</span>'
                : '<span style="color:#cf222e;">● 未运行</span>';
        })
        .catch(function() {
            const statusEl = document.getElementById('frpServiceStatus');
            if (statusEl) statusEl.innerHTML = '<span style="color:#666;">未知</span>';
        });
};

window.frpcControl = function(action) {
    const actions = { 'start': '启动', 'stop': '停止', 'restart': '重启' };
    if (!confirm('确定要' + actions[action] + ' FRP 服务吗？')) return;
    
    __postJson('/api/frp/control', { action: action })
        .then(function(data) {
            if (data && data.success) {
                alert('FRP 服务已' + actions[action]);
                window.frpcRefreshStatus();
                return;
            }
            alert(actions[action] + '失败: ' + ((data && (data.message || data.error)) || '未知错误'));
        })
        .catch(function(err) { alert('请求失败: ' + err.message); });
};

window.openFrpModal = function() { Drawer.open('frpModal'); };
window.closeFrpModal = function() { Drawer.close('frpModal'); };

window.openFrpInEditor = function() {
    window.open('/json/editor?path=/usr/local/frp/frpc.toml', '_blank', 'noopener');
};

window.openClashInEditor = function() {
    const win = window.open('', '_blank');
    if (!win) { alert('弹窗被浏览器拦截，请允许弹窗后重试'); return; }

    const html = [
        '<!DOCTYPE html>',
        '<html lang="zh-CN">',
        '<head>',
        '<meta charset="UTF-8" />',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0" />',
        '<title>Clash 配置编辑</title>',
        '<style>',
        'body{margin:0;font-family:Segoe UI,Tahoma,Geneva,Verdana,sans-serif;background:#f6f8fa;color:#24292f;}',
        '.top{position:sticky;top:0;z-index:10;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px;background:#fff;border-bottom:1px solid #d0d7de;}',
        '.btn{padding:8px 12px;border-radius:8px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:13px;}',
        '.btn.primary{background:#0969da;border-color:#0969da;color:#fff;}',
        '.meta{font-size:12px;color:#57606a;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:70vw;}',
        '#editor{width:100%;height:calc(100vh - 56px);box-sizing:border-box;border:0;outline:none;padding:12px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono","Courier New",monospace;font-size:13px;line-height:1.5;resize:none;}',
        '.status{padding:0 12px 10px;font-size:12px;color:#57606a;}',
        '</style>',
        '</head>',
        '<body>',
        '<div class="top">',
        '<div class="meta" id="meta">正在加载…</div>',
        '<div style="display:flex;gap:8px;align-items:center;">',
        '<button class="btn" id="reloadBtn">刷新</button>',
        '<button class="btn primary" id="saveBtn">保存</button>',
        '</div>',
        '</div>',
        '<textarea id="editor" spellcheck="false"></textarea>',
        '<div class="status" id="status"></div>',
        '<script>',
        '(function(){',
        'var meta=document.getElementById("meta");',
        'var status=document.getElementById("status");',
        'var editor=document.getElementById("editor");',
        'var saveBtn=document.getElementById("saveBtn");',
        'var reloadBtn=document.getElementById("reloadBtn");',
        'var loadedPath="";',
        'var dirty=false;',
        'function setStatus(t){status.textContent=t||"";}',
        'function load(){',
        'setStatus("加载中…");',
        'fetch("/api/clash/config",{credentials:"same-origin"}).then(function(r){return r.json();}).then(function(data){',
        'if(!data||!data.success||!data.data){throw new Error((data&&data.error&&data.error.message)||"加载失败");}',
        'loadedPath=String(data.data.path||"");',
        'meta.textContent=loadedPath?("Clash 配置："+loadedPath):"Clash 配置";',
        'editor.value=String(data.data.content||"");',
        'dirty=false;',
        'setStatus("已加载");',
        '}).catch(function(e){setStatus("加载失败："+(e&&e.message?e.message:String(e)));});',
        '}',
        'function save(){',
        'var content=editor.value;',
        'setStatus("保存中…");',
        'fetch("/api/clash/config",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({content:content})}).then(function(r){return r.json();}).then(function(data){',
        'if(!data||!data.success){throw new Error((data&&data.error&&data.error.message)||(data&&data.message)||"保存失败");}',
        'dirty=false;',
        'setStatus("已保存");',
        '}).catch(function(e){setStatus("保存失败："+(e&&e.message?e.message:String(e)));});',
        '}',
        'editor.addEventListener("input",function(){dirty=true;});',
        'saveBtn.addEventListener("click",function(){save();});',
        'reloadBtn.addEventListener("click",function(){if(dirty&&!confirm("内容未保存，仍要刷新吗？"))return;load();});',
        'window.addEventListener("beforeunload",function(e){if(!dirty)return; e.preventDefault(); e.returnValue="";});',
        'load();',
        '})();',
        '<\/script>',
        '</body>',
        '</html>'
    ].join('');

    win.document.open();
    win.document.write(html);
    win.document.close();
};

window.openFrpProxyDrawer = function() {
    const name = prompt('代理名称:');
    if (!name) return;
    const localPort = prompt('本地端口:');
    if (!localPort) return;
    const remotePort = prompt('远程端口:');
    if (!remotePort) return;
    
    alert('请在编辑器中手动添加代理配置:\n\n[[proxies]]\nname = "' + name + '"\ntype = "tcp"\nlocalIP = "127.0.0.1"\nlocalPort = ' + localPort + '\nremotePort = ' + remotePort);
    window.openFrpInEditor();
};

// ============ Enhanced Clash Management ============
window.loadClashConfigEnhanced = function() {
    const container = document.getElementById('clashContainer');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    
    Promise.all([
        fetch('/api/clash/state', { headers: authHeaders() }).then(r => r.json()),
        fetch('/api/clash/proxies', { headers: authHeaders() }).then(r => r.json())
    ])
    .then(function(results) {
        const statePayload = apiData(results[0]);
        const proxyPayload = apiData(results[1]) || {};
        
        if (!statePayload) {
            container.innerHTML = __errorHtml('加载失败');
            return;
        }
        
        const svc = statePayload.service || {};
        const cfg = statePayload.config || {};
        const proxies = proxyPayload.proxies || [];
        const proxyGroups = proxyPayload.proxy_groups || [];
        const currentSelection = proxyPayload.current_selection || {};
        const ports = proxyPayload.ports || {};
        const rulesCount = proxyPayload.rules_count || 0;
        
        const svcRunning = svc.running;
        const svcText = svcRunning 
            ? '<span style="color:#2da44e;">● 运行中</span>' 
            : '<span style="color:#cf222e;">● 未运行</span>';
        
        let html = '';
        
        // 服务状态
        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">服务状态</div>';
        html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
        html += '<div style="padding:12px;display:flex;justify-content:space-between;align-items:center;">';
        html += '<span style="font-weight:500;">' + (svc.id || 'clash.service') + '</span>';
        html += '<span id="clashServiceStatus" style="font-size:12px;">' + svcText + '</span>';
        html += '</div>';
        html += '<div style="padding:0 12px 12px;display:flex;gap:8px;">';
        html += '<button onclick="clashControl(\'start\')" style="flex:1;padding:8px;border-radius:6px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:13px;">▶ 启动</button>';
        html += '<button onclick="clashControl(\'stop\')" style="flex:1;padding:8px;border-radius:6px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:13px;">⏹ 停止</button>';
        html += '<button onclick="clashControl(\'restart\')" style="flex:1;padding:8px;border-radius:6px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:13px;">🔄 重启</button>';
        html += '</div></div></div>';
        
        // 端口信息
        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">监听端口</div>';
        html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
        if (ports.mixed) html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;"><span style="color:#666;">Mixed</span><span style="font-family:monospace;">' + ports.mixed + '</span></div>';
        if (ports.socks) html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;"><span style="color:#666;">SOCKS</span><span style="font-family:monospace;">' + ports.socks + '</span></div>';
        if (ports.http) html += '<div style="padding:10px 12px;display:flex;justify-content:space-between;"><span style="color:#666;">HTTP</span><span style="font-family:monospace;">' + ports.http + '</span></div>';
        html += '</div></div>';
        
        // 订阅管理
        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">📡 订阅</div>';
        html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
        html += '<div style="padding:12px;">';
        html += '<input type="text" id="clashSubUrl" placeholder="输入订阅URL" style="width:100%;padding:8px;border:1px solid #d0d7de;border-radius:6px;font-size:13px;margin-bottom:8px;box-sizing:border-box;">';
        html += '<div style="display:flex;gap:8px;">';
        html += '<button onclick="clashUpdateSub()" style="flex:1;padding:8px;border-radius:6px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:13px;">🔄 更新订阅</button>';
        html += '<button onclick="openClashInEditor()" style="flex:1;padding:8px;border-radius:6px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:13px;">📝 编辑配置</button>';
        html += '</div></div></div></div>';
        
        // 代理组
        if (proxyGroups.length > 0) {
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">🎯 代理组</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            proxyGroups.forEach(function(group, idx) {
                const current = currentSelection[group] || '未选择';
                html += '<div style="padding:10px 12px;' + (idx < proxyGroups.length - 1 ? 'border-bottom:1px solid #eee;' : '') + '">';
                html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">';
                html += '<span style="font-weight:500;font-size:13px;">' + escapeHtml(group) + '</span>';
                html += '<button onclick="clashOpenProxyList(\'' + escapeHtml(group).replace(/'/g, "\\'") + '\')" style="padding:4px 10px;border-radius:6px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:12px;">切换节点 ▼</button>';
                html += '</div>';
                html += '<div style="font-size:12px;color:#666;">当前: <span style="color:#0969da;">' + escapeHtml(current) + '</span></div>';
                html += '</div>';
            });
            html += '</div></div>';
        }
        
        // 节点列表
        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">📡 节点 (' + proxies.length + ')</div>';
        html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
        if (proxies.length === 0) {
            html += '<div style="padding:20px;text-align:center;color:#666;">暂无数控节点</div>';
        } else {
            html += '<div style="max-height:200px;overflow-y:auto;">';
            proxies.slice(0, 30).forEach(function(proxy, idx) {
                const name = proxy.Name || proxy.name || '-';
                const type = (proxy.type || proxy.Type || '').toUpperCase();
                html += '<div style="padding:8px 12px;' + (idx < Math.min(29, proxies.length - 1) ? 'border-bottom:1px solid #eee;' : '') + 'display:flex;align-items:center;gap:8px;">';
                html += '<span style="color:#58a6ff;">●</span>';
                html += '<span style="font-size:13px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + escapeHtml(name) + '</span>';
                html += '<span style="font-size:11px;color:#666;background:#f3f4f6;padding:2px 6px;border-radius:4px;">' + escapeHtml(type) + '</span>';
                html += '</div>';
            });
            if (proxies.length > 30) {
                html += '<div style="padding:8px 12px;text-align:center;color:#666;font-size:12px;">...共 ' + proxies.length + ' 个节点</div>';
            }
            html += '</div>';
        }
        html += '</div></div>';
        
        // 统计
        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">📊 统计</div>';
        html += '<div style="display:flex;gap:8px;">';
        html += '<div style="flex:1;background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center;"><div style="font-size:24px;font-weight:600;color:#24292f;">' + proxies.length + '</div><div style="font-size:12px;color:#666;">节点</div></div>';
        html += '<div style="flex:1;background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center;"><div style="font-size:24px;font-weight:600;color:#24292f;">' + proxyGroups.length + '</div><div style="font-size:12px;color:#666;">代理组</div></div>';
        html += '<div style="flex:1;background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center;"><div style="font-size:24px;font-weight:600;color:#24292f;">' + rulesCount + '</div><div style="font-size:12px;color:#666;">规则</div></div>';
        html += '</div></div>';
        
        container.innerHTML = html;
    })
    .catch(function(err) {
        console.error(err);
        container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败: ' + escapeHtml(err.message) + '</div>';
    });
};

window.clashUpdateSub = function() {
    const urlInput = document.getElementById('clashSubUrl');
    const url = urlInput ? urlInput.value.trim() : '';
    if (!url) { alert('请输入订阅URL'); return; }
    if (!confirm('更新订阅会合并新节点到现有配置，是否继续？')) return;
    
    __postJson('/api/clash/subscribe', { url: url })
        .then(function(data) {
            if (data && data.success) {
                alert('订阅更新成功！请重启 Clash 服务使配置生效。');
                window.loadClashConfigEnhanced();
            } else {
                alert('更新失败: ' + ((data && (data.message || data.error)) || '未知错误'));
            }
        })
        .catch(function(err) { alert('请求失败: ' + err.message); });
};

window.clashOpenProxyList = function(groupName) {
    fetch('/api/clash/proxies', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            const proxies = payload ? (payload.proxies || []) : [];
            if (proxies.length === 0) { alert('暂无数控节点'); return; }
            
            let html = '<div style="max-height:300px;overflow-y:auto;padding:8px;">';
            proxies.forEach(function(p) {
                const name = p.Name || p.name || '';
                html += '<div onclick="clashSwitchProxy(\'' + escapeHtml(groupName).replace(/'/g, "\\'") + '\', \'' + escapeHtml(name).replace(/'/g, "\\'") + '\')" style="padding:10px 12px;border-bottom:1px solid #eee;cursor:pointer;">';
                html += '<div style="font-weight:500;">' + escapeHtml(name) + '</div>';
                html += '<div style="font-size:12px;color:#666;">' + escapeHtml((p.type || p.Type || '').toUpperCase()) + '</div>';
                html += '</div>';
            });
            html += '</div>';
            
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:20000;display:flex;align-items:center;justify-content:center;';
            modal.innerHTML = '<div style="background:#fff;border-radius:12px;max-width:90%;max-height:80%;overflow:hidden;width:350px;"><div style="padding:16px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="font-weight:500;">选择节点 - ' + escapeHtml(groupName) + '</span><button onclick="this.closest(\'div[style*=fixed]\').remove()" style="border:none;background:none;font-size:20px;cursor:pointer;padding:4px;">×</button></div>' + html + '</div>';
            document.body.appendChild(modal);
        })
        .catch(function(err) { alert('加载节点失败: ' + err.message); });
};

window.clashSwitchProxy = function(groupName, proxyName) {
    if (!confirm('将 ' + groupName + ' 切换到 ' + proxyName + '？')) return;
    __postJson('/api/clash/switch', { group: groupName, proxy: proxyName })
        .then(function(data) {
            if (data && data.success) {
                alert('切换成功！请重启 Clash 服务使配置生效。');
                window.loadClashConfigEnhanced();
            } else {
                alert('切换失败: ' + ((data && (data.message || data.error)) || '未知错误'));
            }
        })
        .catch(function(err) { alert('请求失败: ' + err.message); });
};

// 覆盖原来的打开函数
window.openClashModalOriginal = window.openClashModal;
window.openClashModal = function() { Drawer.open('clashModal'); };
