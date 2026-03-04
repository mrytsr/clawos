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
    var loadingText = (typeof I18n !== 'undefined' ? I18n.t('common.loading_ellipsis') : 'Loading...');
    return '<div style="text-align:center;padding:40px;color:#666;">🔄 ' + escapeHtml(label || loadingText) + '</div>';
}

function __emptyHtml(label) {
    var emptyText = (typeof I18n !== 'undefined' ? I18n.t('common.no_data') : 'No data');
    return '<div style="text-align:center;padding:40px;color:#666;">' + escapeHtml(label || emptyText) + '</div>';
}

function __errorHtml(label) {
    var errorText = (typeof I18n !== 'undefined' ? I18n.t('common.load_failed') : 'Load failed');
    return '<div style="text-align:center;padding:40px;color:#cf222e;">' + escapeHtml(label || errorText) + '</div>';
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
    var loadingText = (typeof I18n !== 'undefined' ? I18n.t('common.loading_ellipsis') : 'Loading...');
    const container = __setContainerHtml('processListContainer', __loadingHtml(loadingText));
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

            var totalProcessText = (typeof I18n !== 'undefined' ? I18n.t('system.process.total') : 'Total Processes');
            var cpuText = (typeof I18n !== 'undefined' ? I18n.t('system.process.cpu') : 'CPU');
            var memoryText = (typeof I18n !== 'undefined' ? I18n.t('system.process.memory') : 'Memory');
            var detailText = (typeof I18n !== 'undefined' ? I18n.t('system.process.detail') : 'Details');
            var killText = (typeof I18n !== 'undefined' ? I18n.t('system.process.kill') : 'Kill');
            const header = '<div style="padding:14px 16px;border-bottom:1px solid #eee;background:#f6f8fa;">'
                + '<div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;">'
                + '<div style="font-weight:600;">' + totalProcessText + '：' + escapeHtml(String(procCount)) + '</div>'
                + '<div style="display:flex;gap:10px;flex-wrap:wrap;font-size:12px;color:#57606a;">'
                + '<span>' + cpuText + '：' + (cpuPct === null ? '-' : escapeHtml(__fmtPct(cpuPct)) + '%') + '</span>'
                + '<span>' + memoryText + '：' + (memUsed === null || memTotal === null ? '-' : escapeHtml(formatSize(memUsed)) + ' / ' + escapeHtml(formatSize(memTotal)) + (memPct === null ? '' : ' (' + escapeHtml(__fmtPct(memPct)) + '%)')) + '</span>'
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
                    + '<button type="button" data-action="proc-detail" data-pid="' + safePid + '" style="border:1px solid #d0d7de;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;">' + detailText + '</button>'
                    + '<button type="button" data-action="proc-kill" data-pid="' + safePid + '" style="border:1px solid #cf222e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#cf222e;">' + killText + '</button>'
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
                    SwalConfirm('结束进程', '确认结束进程 PID ' + pid + '?', function() { killProcess(pid); }, 'warning');
                    if (!ok) return;
                    fetch('/api/process/kill/' + encodeURIComponent(String(pid)), { method: 'POST', headers: authHeaders() })
                        .then(function(r) { return r.json(); })
                        .then(function(data) {
                            const payload = apiData(data);
                            if (payload?.message) {
                                window.showToast(payload.message, payload.success ? 'success' : 'error');
                            } else if (payload?.success) {
                                window.showToast('结束进程成功', 'success');
                            } else {
                                window.showToast('结束进程失败', 'error');
                            }
                            window.loadProcessList();
                        })
                        .catch(function(err) {
                            window.showToast('结束进程失败: ' + err.message, 'error');
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
                SwalConfirm('结束进程', '确认结束进程 PID ' + pid + '?', function() { killProcess(pid); }, 'warning');
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
                    SwalConfirm('卸载确认', '确认卸载 ' + name + '?', function() { uninstallPkg(name); }, 'warning');
                    if (!ok) return;
                    __postJson('/api/system-packages/uninstall', { name: name, manager: manager })
                        .then(function(data) {
                            const payload = apiData(data);
                            if (payload?.success) {
                                window.showToast('卸载成功', 'success');
                            } else {
                                window.showToast(payload?.message || '卸载失败', 'error');
                            }
                            window.loadSystemPackageList();
                        })
                        .catch(function(err) {
                            window.showToast('卸载失败: ' + err.message, 'error');
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
                            if (payload?.success) {
                                window.showToast('安装成功', 'success');
                            } else {
                                window.showToast(payload?.message || '安装失败', 'error');
                            }
                            __renderPkgList(containerId, options);
                        })
                        .catch(function(err) {
                            window.showToast('安装失败: ' + err.message, 'error');
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
                    SwalConfirm('卸载确认', '确认卸载 ' + name + '?', function() { uninstallPkg(name); }, 'warning');
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
                        SwalConfirm('删除镜像', '确认删除镜像 ' + id + '?', function() { removeImage(id); }, 'warning');
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
                                if (payload?.success) {
                                    window.showToast('操作成功', 'success');
                                } else {
                                    window.showToast(payload?.message || '操作失败', 'error');
                                }
                                window.loadDockerTabs('containers');
                            })
                            .catch(function(err) {
                                window.showToast('操作失败: ' + err.message, 'error');
                            });
                    });
                });

                Array.from(containersEl.querySelectorAll('button[data-action="docker-ctr-rm"]')).forEach(function(btn) {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        const id = btn.getAttribute('data-id') || '';
                        if (!id) return;
                        SwalConfirm('删除容器', '确认删除容器 ' + id + '?', function() { removeContainer(id); }, 'warning');
                        if (!ok) return;
                        __postJson('/api/docker/container/rm', { id: id, force: true })
                            .then(function(data) {
                                const payload = apiData(data);
                                if (payload?.success) {
                                    window.showToast('删除成功', 'success');
                                } else {
                                    window.showToast(payload?.message || '删除失败', 'error');
                                }
                                window.loadDockerTabs('containers');
                            })
                            .catch(function(err) {
                                window.showToast('删除失败: ' + err.message, 'error');
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

// 删除 systemd 服务
window.__systemdRemove = function(service, scope) {
    const svc = String(service || '');
    const scp = scope || 'user';
    if (!svc) return;
    if (!confirm('确定要删除服务 ' + svc + ' 吗？此操作不可恢复。')) return;
    
    __postJson('/api/systemd/remove', { service: svc, scope: scp })
        .then(function(data) {
            if (apiSuccess(data)) {
                if (typeof window.showToast === 'function') window.showToast('删除成功', 'success');
                window.loadSystemdList();
            } else {
                if (typeof window.showToast === 'function') window.showToast(apiMessage(data) || '删除失败', 'error');
            }
        })
        .catch(function() {
            if (typeof window.showToast === 'function') window.showToast('删除失败', 'error');
        });
};

// 编辑 systemd 服务配置文件
window.__systemdEditConfig = function(service, scope) {
    const svc = String(service || '');
    const scp = scope || window._systemdCurrentScope || 'user';
    console.log('Edit config:', svc, scp);
    if (!svc) {
        if (typeof window.showToast === 'function') window.showToast('服务名无效', 'error');
        return;
    }
    
    const url = '/api/systemd/config_path?service=' + encodeURIComponent(svc) + '&scope=' + encodeURIComponent(scp);
    console.log('Fetching:', url);
    
    // 先获取配置文件路径
    fetch(url, { headers: authHeaders() })
        .then(function(r) { 
            console.log('Response status:', r.status);
            return r.json(); 
        })
        .then(function(data) {
            console.log('Response data:', data);
            if (data.success && data.data && data.data.path) {
                const configPath = data.data.path;
                console.log('Config path:', configPath);
                // 用代码编辑器打开
                if (typeof window.openEditor === 'function') {
                    window.openEditor(configPath);
                } else {
                    // 备用：打开文件管理器到该目录
                    window.openFolder(configPath);
                }
            } else {
                if (typeof window.showToast === 'function') {
                    window.showToast(data.message || '未找到配置文件', 'error');
                }
            }
        })
        .catch(function(err) {
            console.error('Fetch error:', err);
            if (typeof window.showToast === 'function') window.showToast('获取配置文件失败', 'error');
        });
};

window.loadSystemdList = function() {
    const container = __setContainerHtml('systemdListContainer', __loadingHtml('加载中...'));
    
    // 先加载 User tab（默认显示）
    fetch('/api/systemd/list?scope=user', { headers: authHeaders() })
        .then(r => r.json())
        .then(function(data) {
            if (!container) return;
            const userData = apiData(data) || { services: [] };
            const userServices = Array.isArray(userData.services) ? userData.services : [];
            
            // 更新计数
            document.getElementById('systemdUserCount').textContent = userServices.length;
            
            // 保存 User 数据
            window._systemdData = { user: userServices, system: [] };
            window._systemdSystemLoaded = false;
            
            // 默认显示 User
            window.switchSystemdTab('user');
            
            // 后台加载 System tab
            fetch('/api/systemd/list?scope=system', { headers: authHeaders() })
                .then(r => r.json())
                .then(function(sysData) {
                    const systemData = apiData(sysData) || { services: [] };
                    const systemServices = Array.isArray(systemData.services) ? systemData.services : [];
                    
                    window._systemdData.system = systemServices;
                    window._systemdSystemLoaded = true;
                    document.getElementById('systemdSystemCount').textContent = systemServices.length;
                })
                .catch(function() {
                    document.getElementById('systemdSystemCount').textContent = '?';
                });
        })
        .catch(function() {
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
    
    const container = document.getElementById('systemdListContainer');
    if (!container) return;
    
    // 如果是 System tab 且还没加载，显示 loading 并触发加载
    if (scope === 'system' && !window._systemdSystemLoaded) {
        container.innerHTML = __loadingHtml('加载中...');
        fetch('/api/systemd/list?scope=system', { headers: authHeaders() })
            .then(r => r.json())
            .then(function(sysData) {
                const systemData = apiData(sysData) || { services: [] };
                const systemServices = Array.isArray(systemData.services) ? systemData.services : [];
                window._systemdData.system = systemServices;
                window._systemdSystemLoaded = true;
                document.getElementById('systemdSystemCount').textContent = systemServices.length;
                window.switchSystemdTab('system'); // 重新渲染
            })
            .catch(function() {
                container.innerHTML = __errorHtml('加载失败');
            });
        return;
    }
    
    // 获取搜索关键词
    const searchInput = document.getElementById('systemdSearch');
    const keyword = (searchInput?.value || '').toLowerCase();
    
    // 过滤并渲染
    const data = window._systemdData || { user: [], system: [] };
    const services = scope === 'user' ? data.user : data.system;
    const filtered = keyword ? services.filter(s => s.name.toLowerCase().includes(keyword)) : services;
    
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
        const enabledBadgeColor = enabled ? '#0969da' : '#8b8b8b';
        const enabledBadgeText = enabled ? 'enabled' : 'disabled';
        const scope = window._systemdCurrentScope || 'user';

        // 构建菜单项 - 使用 function + actionParams
        var menuItems = [
            { label: escapeHtml(String(name)), icon: '', action: null, disabled: true }
        ];
        if (enabled) {
            menuItems.push({ label: '禁用开机启动', icon: '🚫', action: __systemdControl, actionParams: [name, 'disable', scope] });
        } else {
            menuItems.push({ label: '启用开机启动', icon: '✅', action: __systemdControl, actionParams: [name, 'enable', scope] });
        }
        menuItems.push({ label: '启动', icon: '▶', action: __systemdControl, actionParams: [name, 'start', scope] });
        menuItems.push({ label: '停止', icon: '⏹', action: __systemdControl, actionParams: [name, 'stop', scope] });
        menuItems.push({ label: '重启', icon: '🔄', action: __systemdControl, actionParams: [name, 'restart', scope] });
        menuItems.push({ label: '查看日志', icon: '📋', action: openServiceLog, actionParams: escapeHtml(String(name)) });
        menuItems.push({ label: '编辑配置文件', icon: '✏️', action: __systemdEditConfig, actionParams: [name, scope] });
        menuItems.push({ label: '删除服务', icon: '🗑', action: __systemdRemove, actionParams: [name, scope], danger: true });

        // 使用 SmallMenu 生成菜单
        var menuResult = SmallMenu.render({
            triggerText: '⋮',
            items: menuItems
        });

        return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;">'
            + '<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">'
            + '<div style="min-width:0;">'
            + '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">'
            + '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(String(name)) + '</div>'
            + '<span style="font-size:11px;padding:2px 8px;border-radius:999px;background:' + badgeColor + ';color:#fff;">' + escapeHtml(String(badgeText)) + '</span>'
            + '<span style="font-size:11px;padding:2px 8px;border-radius:999px;background:' + enabledBadgeColor + ';color:#fff;">' + enabledBadgeText + '</span>'
            + '</div>'
            + (desc ? '<div style="font-size:12px;color:#57606a;margin-top:2px;word-break:break-word;">' + escapeHtml(String(desc)) + '</div>' : '')
            + '<div style="font-size:12px;color:#57606a;margin-top:2px;">' + escapeHtml(String(active)) + (sub ? ' (' + escapeHtml(String(sub)) + ')' : '') + '</div>'
            + (sinceAgo ? '<div style="font-size:12px;color:#57606a;margin-top:2px;">启动于 ' + escapeHtml(String(sinceAgo)) + '</div>' : '')
            + '</div>'
            + menuResult
            + '</div>'
            + '</div>';
    }).join('') + '</div>';

    // 绑定其他 systemd 按钮事件
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
    window.switchSystemdTab(scope);
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

function __serviceButtons(serviceKey) {
    var prefix = String(serviceKey || '');
    return {
        install: document.getElementById(prefix + 'InstallBtn'),
        reinstall: document.getElementById(prefix + 'ReinstallBtn'),
        uninstall: document.getElementById(prefix + 'UninstallBtn')
    };
}

function __renderServiceInstallButtons(serviceKey, installed) {
    var btns = __serviceButtons(serviceKey);
    if (!btns.install || !btns.reinstall || !btns.uninstall) return;
    btns.install.style.display = installed ? 'none' : 'inline-flex';
    btns.reinstall.style.display = installed ? 'inline-flex' : 'none';
    btns.uninstall.style.display = installed ? 'inline-flex' : 'none';
}

function __setServiceButtonsDisabled(serviceKey, disabled) {
    var btns = __serviceButtons(serviceKey);
    Object.keys(btns).forEach(function(k) {
        var el = btns[k];
        if (!el) return;
        el.disabled = !!disabled;
        el.style.opacity = disabled ? '0.6' : '1';
        el.style.cursor = disabled ? 'not-allowed' : 'pointer';
    });
}

function __serviceInstallUrl(serviceKey, action) {
    var k = String(serviceKey || '');
    var a = String(action || '');
    if (k === 'ollama') return '/api/ollama/' + a;
    if (k === 'openclaw') return '/api/openclaw/' + a;
    if (k === 'clash') return '/api/clash/' + a;
    if (k === 'frp') return '/api/frp/' + a;
    return '';
}

window.refreshServiceInstallState = function(serviceKey) {
    var url = __serviceInstallUrl(serviceKey, 'install_state');
    if (!url) return Promise.resolve(null);
    __setServiceButtonsDisabled(serviceKey, true);
    return fetch(url, { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var payload = apiData(data);
            var installed = !!(payload && payload.installed);
            __renderServiceInstallButtons(serviceKey, installed);
            return payload;
        })
        .catch(function() {
            __renderServiceInstallButtons(serviceKey, false);
            return null;
        })
        .finally(function() {
            __setServiceButtonsDisabled(serviceKey, false);
        });
};

window.serviceInstallAction = function(serviceKey, action) {
    var url = __serviceInstallUrl(serviceKey, action);
    if (!url) return;
    var actionText = action === 'install' ? '安装' : action === 'reinstall' ? '重新安装' : '卸载';
    SwalConfirm('确认操作', '确定要' + actionText + '吗？', function() {
        __setServiceButtonsDisabled(serviceKey, true);
        __postJson(url, {})
            .then(function(resp) {
                if (!resp || !resp.success) {
                    SwalAlert('操作失败', (resp && (resp.message || (resp.error && resp.error.message))) || '未知错误', 'error');
                    return;
                }
                var taskId = (resp.data && resp.data.taskId) || resp.taskId;
                if (taskId && window.TaskPoller && typeof window.TaskPoller.start === 'function') {
                    showToast(actionText + '已开始…', 'info');
                    if (window.__activeTaskPoller && typeof window.__activeTaskPoller.cancel === 'function') {
                        window.__activeTaskPoller.cancel();
                    }
                    window.__activeTaskPoller = window.TaskPoller.start(taskId, { intervalMs: 1000, timeoutMs: 10 * 60 * 1000 });
                    window.__activeTaskPoller.promise.then(function(res) {
                        if (res && res.ok) showToast(actionText + '成功', 'success');
                        else showToast(actionText + '失败', 'error');
                        window.refreshServiceInstallState(serviceKey);
                        if (serviceKey === 'ollama') window.loadOllamaModels();
                        if (serviceKey === 'openclaw') window.loadOpenclawConfig();
                        if (serviceKey === 'clash') window.loadClashConfigEnhanced();
                        if (serviceKey === 'frp') window.loadFrpConfig();
                    });
                    return;
                }
                showToast(actionText + '完成', 'success');
                window.refreshServiceInstallState(serviceKey);
            })
            .catch(function(err) {
                showToast('请求失败: ' + err.message, 'error');
            })
            .finally(function() {
                __setServiceButtonsDisabled(serviceKey, false);
            });
    }, 'warning');
};

// Ollama模型
window.loadOllamaModels = function() {
    window.refreshServiceInstallState('ollama');
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

function renderOpenclawChannelsCard(channels) {
    const safeChannels = channels || {};
    const channelNames = Object.keys(safeChannels);
    let html = '';
    html += '<div style="margin-bottom:16px;">';
    html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">Channels</div>';
    html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
    if (!channelNames.length) {
        html += '<div style="padding:12px;color:#57606a;font-size:13px;">暂无 Channels</div>';
        html += '</div></div>';
        return html;
    }
    channelNames.forEach(function(ch, idx) {
        const cfg = safeChannels[ch] || {};
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
    return html;
}

window.loadOpenclawConfig = function() {
    window.refreshServiceInstallState('openclaw');
    let container = null;
    const botDrawer = document.getElementById('botDrawer');
    const botPanel = document.getElementById('botConfigPanel');
    if (botDrawer && botDrawer.classList.contains('open') && botPanel && botPanel.style.display !== 'none') {
        container = document.getElementById('botOpenclawConfigContainer');
    }
    if (!container) container = document.getElementById('openclawConfigContainer') || document.getElementById('botOpenclawConfigContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    
    fetch('/api/openclaw/status', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (!payload || !container) return;
            
            let html = '';
            
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;display:flex;justify-content:space-between;align-items:center;">';
            html += '<span>⏰ 定时任务</span>';
            html += '<button onclick="openCronAddModal()" style="background:#0969da;border:none;border-radius:6px;color:#fff;padding:4px 10px;cursor:pointer;font-size:12px;">+ 添加</button>';
            html += '</div>';
            html += '<div id="cronJobList" style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            html += '<div style="padding:20px;text-align:center;color:#666;">加载中...</div>';
            html += '</div>';
            html += '</div>';

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
            setTimeout(function() { if (typeof loadCronJobList === 'function') loadCronJobList(); }, 50);
        })
        .catch(function(err) {
            console.error(err);
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败</div>';
        });
};

function renderOpenclawAgentsList(agents) {
    const list = Array.isArray(agents) ? agents : [];
    let html = '';
    html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
    if (!list.length) {
        html += '<div style="padding:12px;color:#57606a;font-size:13px;">暂无 Agents</div>';
        html += '</div>';
        return html;
    }
    list.forEach(function(agent, idx) {
        const status = agent && agent.status ? agent.status : 'pending';
        const dot = status === 'ok' ? '#2da44e' : '#cf222e';
        html += '<div style="padding:10px 12px;' + (idx < list.length - 1 ? 'border-bottom:1px solid #eee;' : '') + 'display:flex;align-items:flex-start;justify-content:space-between;gap:12px;">';
        html += '<div style="min-width:0;">';
        html += '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">';
        html += '<span style="width:8px;height:8px;border-radius:50%;background:' + dot + ';display:inline-block;"></span>';
        html += '<span style="font-weight:600;font-size:14px;word-break:break-all;">' + escapeHtml((agent && (agent.name || agent.id)) || '-') + '</span>';
        html += '<span style="font-size:11px;padding:1px 6px;border-radius:999px;background:#f6f8fa;color:#57606a;">' + ((agent && agent.sessions) || 0) + ' 会话</span>';
        html += '</div>';
        html += '<div style="font-size:12px;color:#57606a;margin-top:4px;">' + escapeHtml((agent && agent.active_ago) || '-') + '</div>';
        html += '</div>';
        html += '<div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">';
        html += '<button onclick="openOpenclawEditAgentModal(\'' + ((agent && agent.id) || '') + '\')" style="background:#0969da;border:none;border-radius:6px;color:#fff;padding:6px 10px;cursor:pointer;font-size:12px;">编辑</button>';
        html += '<button onclick="openclawRemoveAgent(\'' + ((agent && agent.id) || '') + '\')" style="background:#cf222e;border:none;border-radius:6px;color:#fff;padding:6px 10px;cursor:pointer;font-size:12px;">删除</button>';
        html += '</div>';
        html += '</div>';
    });
    html += '</div>';
    return html;
}

window.loadOpenclawAgents = function() {
    let container = document.getElementById('botOpenclawAgentsContainer');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/openclaw/agents/list', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!payload || !container) return;
            container.innerHTML = renderOpenclawAgentsList(payload.agents || []);
        })
        .catch(function(err) {
            console.error(err);
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败</div>';
        });
};

window.openOpenclawAddAgentModal = function() {
    if (window.SwalGitHub && typeof window.SwalGitHub.fire === 'function') {
        window.SwalGitHub.fire({
            title: '添加 Agent',
            html: '<div style="text-align:left;">' +
                '<div style="font-size:12px;color:#57606a;margin-bottom:6px;">Agent ID（仅支持字母数字、._-）</div>' +
                '<input id="openclawAgentIdInput" class="swal2-input" placeholder="agent_id" style="width:100%;box-sizing:border-box;">' +
                '</div>',
            focusConfirm: false,
            showCancelButton: true,
            confirmButtonText: '添加',
            cancelButtonText: '取消',
            preConfirm: function() {
                const el = document.getElementById('openclawAgentIdInput');
                const v = (el && el.value ? el.value : '').trim();
                if (!v) {
                    window.SwalGitHub.showValidationMessage('请输入 Agent ID');
                    return false;
                }
                return { id: v };
            }
        }).then(function(res) {
            if (!res || !res.isConfirmed || !res.value) return;
            fetch('/api/openclaw/agents/add', {
                method: 'POST',
                headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
                body: JSON.stringify({ id: res.value.id })
            })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (!data || !data.success) {
                        const msg = (data && data.error && data.error.message) ? data.error.message : '添加失败';
                        alert(msg);
                        return;
                    }
                    if (typeof window.loadOpenclawAgents === 'function') window.loadOpenclawAgents();
                })
                .catch(function(err) {
                    console.error(err);
                    alert('添加失败');
                });
        });
        return;
    }
    const v = prompt('请输入 Agent ID（仅支持字母数字、._-）');
    if (!v) return;
    fetch('/api/openclaw/agents/add', {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
        body: JSON.stringify({ id: v.trim() })
    })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data || !data.success) {
                const msg = (data && data.error && data.error.message) ? data.error.message : '添加失败';
                alert(msg);
                return;
            }
            if (typeof window.loadOpenclawAgents === 'function') window.loadOpenclawAgents();
        })
        .catch(function(err) {
            console.error(err);
            alert('添加失败');
        });
};

window.openOpenclawEditAgentModal = function(agentId) {
    const oldId = (agentId || '').toString().trim();
    if (!oldId) return;
    if (window.SwalGitHub && typeof window.SwalGitHub.fire === 'function') {
        window.SwalGitHub.fire({
            title: '编辑 Agent',
            html: '<div style="text-align:left;">' +
                '<div style="font-size:12px;color:#57606a;margin-bottom:6px;">Agent ID（重命名）</div>' +
                '<input id="openclawAgentRenameInput" class="swal2-input" placeholder="agent_id" style="width:100%;box-sizing:border-box;" value="' + escapeHtml(oldId) + '">' +
                '</div>',
            focusConfirm: false,
            showCancelButton: true,
            confirmButtonText: '保存',
            cancelButtonText: '取消',
            preConfirm: function() {
                const el = document.getElementById('openclawAgentRenameInput');
                const v = (el && el.value ? el.value : '').trim();
                if (!v) {
                    window.SwalGitHub.showValidationMessage('请输入 Agent ID');
                    return false;
                }
                return { id: v };
            }
        }).then(function(res) {
            if (!res || !res.isConfirmed || !res.value) return;
            const newId = (res.value.id || '').trim();
            fetch('/api/openclaw/agents/rename', {
                method: 'POST',
                headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
                body: JSON.stringify({ from: oldId, to: newId })
            })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (!data || !data.success) {
                        const msg = (data && data.error && data.error.message) ? data.error.message : '保存失败';
                        alert(msg);
                        return;
                    }
                    if (typeof window.loadOpenclawAgents === 'function') window.loadOpenclawAgents();
                })
                .catch(function(err) {
                    console.error(err);
                    alert('保存失败');
                });
        });
        return;
    }
    const v = prompt('请输入新的 Agent ID', oldId);
    if (!v) return;
    fetch('/api/openclaw/agents/rename', {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
        body: JSON.stringify({ from: oldId, to: v.trim() })
    })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data || !data.success) {
                const msg = (data && data.error && data.error.message) ? data.error.message : '保存失败';
                alert(msg);
                return;
            }
            if (typeof window.loadOpenclawAgents === 'function') window.loadOpenclawAgents();
        })
        .catch(function(err) {
            console.error(err);
            alert('保存失败');
        });
};

window.openclawRemoveAgent = function(agentId) {
    const id = (agentId || '').toString().trim();
    if (!id) return;
    if (window.SwalGitHub && typeof window.SwalGitHub.fire === 'function') {
        window.SwalGitHub.fire({
            title: '删除 Agent？',
            text: id,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: '删除',
            cancelButtonText: '取消'
        }).then(function(res) {
            if (!res || !res.isConfirmed) return;
            fetch('/api/openclaw/agents/remove', {
                method: 'POST',
                headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
                body: JSON.stringify({ id: id })
            })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (!data || !data.success) {
                        const msg = (data && data.error && data.error.message) ? data.error.message : '删除失败';
                        alert(msg);
                        return;
                    }
                    if (typeof window.loadOpenclawAgents === 'function') window.loadOpenclawAgents();
                })
                .catch(function(err) {
                    console.error(err);
                    alert('删除失败');
                });
        });
        return;
    }
    const ok = confirm('确定删除 Agent ' + id + ' 吗？');
    if (!ok) return;
    fetch('/api/openclaw/agents/remove', {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
        body: JSON.stringify({ id: id })
    })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data || !data.success) {
                const msg = (data && data.error && data.error.message) ? data.error.message : '删除失败';
                alert(msg);
                return;
            }
            if (typeof window.loadOpenclawAgents === 'function') window.loadOpenclawAgents();
        })
        .catch(function(err) {
            console.error(err);
            alert('删除失败');
        });
};

window.loadOpenclawChannels = function() {
    let container = document.getElementById('botOpenclawChannelsContainer');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/openclaw/channels/list', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!payload || !container) return;
            container.innerHTML = renderOpenclawChannelsManageList(payload.channels || []);
        })
        .catch(function(err) {
            console.error(err);
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败</div>';
        });
};

function renderOpenclawChannelsManageList(channels) {
    const list = Array.isArray(channels) ? channels : [];
    let html = '';
    html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
    if (!list.length) {
        html += '<div style="padding:12px;color:#57606a;font-size:13px;">暂无 Channels</div>';
        html += '</div>';
        return html;
    }

    list.forEach(function(ch, idx) {
        const name = (ch && ch.name) ? ch.name : '';
        const enabled = !!(ch && ch.enabled);
        html += '<div style="padding:10px 12px;' + (idx < list.length - 1 ? 'border-bottom:1px solid #eee;' : '') + 'display:flex;align-items:center;justify-content:space-between;gap:12px;">';
        html += '<div style="min-width:0;">';
        html += '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">';
        html += '<span style="font-weight:600;font-size:14px;text-transform:capitalize;">' + escapeHtml(name || '-') + '</span>';
        html += enabled
            ? '<span style="font-size:11px;padding:1px 6px;border-radius:999px;background:#dafbe1;color:#1a7f37;">已启用</span>'
            : '<span style="font-size:11px;padding:1px 6px;border-radius:999px;background:#ffebe9;color:#cf222e;">已禁用</span>';
        html += '</div>';
        html += '<div style="font-family:ui-monospace;font-size:12px;color:#57606a;word-break:break-all;margin-top:4px;">' + escapeHtml(name || '-') + '</div>';
        html += '</div>';
        html += '<div style="display:flex;align-items:center;gap:10px;flex-shrink:0;">';
        html += '<label style="display:flex;align-items:center;gap:6px;font-size:12px;color:#57606a;cursor:pointer;">';
        html += '<input type="checkbox" ' + (enabled ? 'checked' : '') + ' onchange="openclawToggleChannelEnabled(' + JSON.stringify(name) + ', this.checked)" />';
        html += '<span>启用</span>';
        html += '</label>';
        html += '<button onclick="openOpenclawEditChannelModal(' + JSON.stringify(name) + ',' + (enabled ? 'true' : 'false') + ')" style="background:#0969da;border:none;border-radius:6px;color:#fff;padding:6px 10px;cursor:pointer;font-size:12px;">编辑</button>';
        html += '<button onclick="openclawRemoveChannel(' + JSON.stringify(name) + ')" style="background:#cf222e;border:none;border-radius:6px;color:#fff;padding:6px 10px;cursor:pointer;font-size:12px;">删除</button>';
        html += '</div>';
        html += '</div>';
    });
    html += '</div>';
    return html;
}

window.openOpenclawAddChannelModal = function() {
    if (!(window.SwalGitHub && typeof window.SwalGitHub.fire === 'function')) {
        alert('弹窗组件未加载');
        return;
    }
    window.SwalGitHub.fire({
        title: '添加 Channel',
        html: '<div style="text-align:left;">' +
            '<div style="font-size:12px;color:#57606a;margin-bottom:6px;">名称（仅支持字母数字、._-）</div>' +
            '<input id="openclawChannelNameInput" class="swal2-input" placeholder="telegram / wechat / discord" style="width:100%;box-sizing:border-box;">' +
            '<label style="display:flex;align-items:center;gap:8px;margin-top:10px;font-size:13px;color:#24292f;">' +
            '<input id="openclawChannelEnabledInput" type="checkbox" checked /> 启用' +
            '</label>' +
            '</div>',
        focusConfirm: false,
        showCancelButton: true,
        confirmButtonText: '添加',
        cancelButtonText: '取消',
        preConfirm: function() {
            const nameEl = document.getElementById('openclawChannelNameInput');
            const enabledEl = document.getElementById('openclawChannelEnabledInput');
            const name = (nameEl && nameEl.value ? nameEl.value : '').trim();
            const enabled = !!(enabledEl && enabledEl.checked);
            if (!name) {
                window.SwalGitHub.showValidationMessage('请输入名称');
                return false;
            }
            return { name: name, enabled: enabled };
        }
    }).then(function(res) {
        if (!res || !res.isConfirmed || !res.value) return;
        fetch('/api/openclaw/channels/add', {
            method: 'POST',
            headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
            body: JSON.stringify({ name: res.value.name, enabled: res.value.enabled })
        })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (!data || !data.success) {
                    const msg = (data && data.error && data.error.message) ? data.error.message : '添加失败';
                    alert(msg);
                    return;
                }
                if (typeof window.loadOpenclawChannels === 'function') window.loadOpenclawChannels();
            })
            .catch(function(err) {
                console.error(err);
                alert('添加失败');
            });
    });
};

window.openOpenclawEditChannelModal = function(channelName, enabled) {
    const name = (channelName || '').toString().trim();
    if (!name) return;
    if (!(window.SwalGitHub && typeof window.SwalGitHub.fire === 'function')) {
        alert('弹窗组件未加载');
        return;
    }
    window.SwalGitHub.fire({
        title: '编辑 Channel',
        html: '<div style="text-align:left;">' +
            '<div style="font-size:12px;color:#57606a;margin-bottom:6px;">名称（重命名）</div>' +
            '<input id="openclawChannelNewNameInput" class="swal2-input" placeholder="channel_name" style="width:100%;box-sizing:border-box;" value="' + escapeHtml(name) + '">' +
            '<label style="display:flex;align-items:center;gap:8px;margin-top:10px;font-size:13px;color:#24292f;">' +
            '<input id="openclawChannelNewEnabledInput" type="checkbox" ' + (enabled ? 'checked' : '') + ' /> 启用' +
            '</label>' +
            '</div>',
        focusConfirm: false,
        showCancelButton: true,
        confirmButtonText: '保存',
        cancelButtonText: '取消',
        preConfirm: function() {
            const nameEl = document.getElementById('openclawChannelNewNameInput');
            const enabledEl = document.getElementById('openclawChannelNewEnabledInput');
            const newName = (nameEl && nameEl.value ? nameEl.value : '').trim();
            const newEnabled = !!(enabledEl && enabledEl.checked);
            if (!newName) {
                window.SwalGitHub.showValidationMessage('请输入名称');
                return false;
            }
            return { name: name, newName: newName, enabled: newEnabled };
        }
    }).then(function(res) {
        if (!res || !res.isConfirmed || !res.value) return;
        const payload = { name: res.value.name, enabled: res.value.enabled };
        if (res.value.newName && res.value.newName !== res.value.name) payload.newName = res.value.newName;
        fetch('/api/openclaw/channels/update', {
            method: 'POST',
            headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
            body: JSON.stringify(payload)
        })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (!data || !data.success) {
                    const msg = (data && data.error && data.error.message) ? data.error.message : '保存失败';
                    alert(msg);
                    return;
                }
                if (typeof window.loadOpenclawChannels === 'function') window.loadOpenclawChannels();
            })
            .catch(function(err) {
                console.error(err);
                alert('保存失败');
            });
    });
};

window.openclawToggleChannelEnabled = function(channelName, enabled) {
    const name = (channelName || '').toString().trim();
    if (!name) return;
    fetch('/api/openclaw/channels/update', {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
        body: JSON.stringify({ name: name, enabled: !!enabled })
    })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data || !data.success) {
                const msg = (data && data.error && data.error.message) ? data.error.message : '更新失败';
                alert(msg);
                if (typeof window.loadOpenclawChannels === 'function') window.loadOpenclawChannels();
            }
        })
        .catch(function(err) {
            console.error(err);
            alert('更新失败');
            if (typeof window.loadOpenclawChannels === 'function') window.loadOpenclawChannels();
        });
};

window.openclawRemoveChannel = function(channelName) {
    const name = (channelName || '').toString().trim();
    if (!name) return;
    if (!(window.SwalGitHub && typeof window.SwalGitHub.fire === 'function')) {
        alert('弹窗组件未加载');
        return;
    }
    window.SwalGitHub.fire({
        title: '删除 Channel？',
        text: name,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: '删除',
        cancelButtonText: '取消'
    }).then(function(res) {
        if (!res || !res.isConfirmed) return;
        fetch('/api/openclaw/channels/remove', {
            method: 'POST',
            headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
            body: JSON.stringify({ name: name })
        })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (!data || !data.success) {
                    const msg = (data && data.error && data.error.message) ? data.error.message : '删除失败';
                    alert(msg);
                    return;
                }
                if (typeof window.loadOpenclawChannels === 'function') window.loadOpenclawChannels();
            })
            .catch(function(err) {
                console.error(err);
                alert('删除失败');
            });
    });
};

window.loadOpenclawModels = function() {
    let container = document.getElementById('botOpenclawModelsContainer');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/openclaw/models/list', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!payload || !container) return;
            const models = payload.models || [];
            const defaultModelId = payload.defaultModelId || '';
            let html = '';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            if (!models.length) {
                html += '<div style="padding:12px;color:#57606a;font-size:13px;">暂无模型</div>';
                html += '</div>';
                container.innerHTML = html;
                return;
            }
            models.forEach(function(m, idx) {
                const isDefault = !!m.default || (defaultModelId && m.id === defaultModelId);
                html += '<div style="padding:10px 12px;' + (idx < models.length - 1 ? 'border-bottom:1px solid #eee;' : '') + 'display:flex;align-items:center;justify-content:space-between;gap:12px;">';
                html += '<div style="min-width:0;">';
                html += '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">';
                html += '<span style="font-weight:600;font-size:14px;">' + escapeHtml(m.name || m.id || '-') + '</span>';
                html += '<span style="font-size:11px;padding:1px 6px;border-radius:999px;background:#ddf4ff;color:#0969da;">' + escapeHtml(m.provider || '-') + '</span>';
                if (m.reasoning) {
                    html += '<span style="font-size:11px;padding:1px 6px;border-radius:999px;background:#fff8c5;color:#9a6700;">reasoning</span>';
                }
                if (isDefault) {
                    html += '<span style="font-size:11px;padding:1px 6px;border-radius:999px;background:#dafbe1;color:#1a7f37;">默认</span>';
                }
                html += '</div>';
                html += '<div style="font-family:ui-monospace;font-size:12px;color:#57606a;word-break:break-all;">' + escapeHtml(m.id || '-') + '</div>';
                html += '</div>';
                html += '<div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">';
                if (isDefault) {
                    html += '<span style="font-size:12px;padding:6px 10px;border-radius:6px;background:#dafbe1;color:#1a7f37;">默认</span>';
                } else {
                    html += '<button onclick="openclawSetDefaultModel(' + JSON.stringify(m.id || '') + ')" style="background:#2da44e;border:none;border-radius:6px;color:#fff;padding:6px 10px;cursor:pointer;font-size:12px;">设为默认</button>';
                }
                html += '<button onclick="openclawRemoveModel(' + JSON.stringify(m.provider || '') + ',' + JSON.stringify(m.id || '') + ')" style="background:#cf222e;border:none;border-radius:6px;color:#fff;padding:6px 10px;cursor:pointer;font-size:12px;">删除</button>';
                html += '</div>';
                html += '</div>';
            });
            html += '</div>';
            container.innerHTML = html;
        })
        .catch(function(err) {
            console.error(err);
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败</div>';
        });
};

window.openclawSetDefaultModel = function(modelId) {
    const mid = (modelId || '').toString().trim();
    if (!mid) return;
    fetch('/api/openclaw/models/set_default', {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
        body: JSON.stringify({ modelId: mid })
    })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data || !data.success) {
                const msg = (data && data.error && data.error.message) ? data.error.message : '设置失败';
                alert(msg);
                return;
            }
            if (typeof window.loadOpenclawModels === 'function') window.loadOpenclawModels();
        })
        .catch(function(err) {
            console.error(err);
            alert('设置失败');
        });
};

window.openclawRemoveModel = function(provider, modelId) {
    const mid = (modelId || '').toString().trim();
    const p = (provider || '').toString().trim();
    if (!mid) return;
    const ok = confirm('确定删除模型 ' + mid + ' 吗？');
    if (!ok) return;
    fetch('/api/openclaw/models/remove', {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
        body: JSON.stringify({ provider: p, modelId: mid })
    })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data || !data.success) {
                const msg = (data && data.error && data.error.message) ? data.error.message : '删除失败';
                alert(msg);
                return;
            }
            if (typeof window.loadOpenclawModels === 'function') window.loadOpenclawModels();
        })
        .catch(function(err) {
            console.error(err);
            alert('删除失败');
        });
};

window.openOpenclawAddModelModal = function() {
    if (!(window.SwalGitHub && typeof window.SwalGitHub.fire === 'function')) {
        alert('弹窗组件未加载');
        return;
    }
    window.SwalGitHub.fire({
        title: '添加模型',
        html: '<div style="text-align:left;">' +
            '<div style="font-size:12px;color:#57606a;margin-bottom:6px;">Provider</div>' +
            '<input id="openclawModelProviderInput" class="swal2-input" placeholder="default / openai / anthropic" style="width:100%;box-sizing:border-box;" value="default">' +
            '<div style="font-size:12px;color:#57606a;margin-bottom:6px;">Model ID</div>' +
            '<input id="openclawModelIdInput" class="swal2-input" placeholder="gpt-4.1 / claude-3.5-sonnet" style="width:100%;box-sizing:border-box;">' +
            '<div style="font-size:12px;color:#57606a;margin-bottom:6px;">显示名称（可留空）</div>' +
            '<input id="openclawModelNameInput" class="swal2-input" placeholder="Display Name" style="width:100%;box-sizing:border-box;">' +
            '<label style="display:flex;align-items:center;gap:8px;margin-top:10px;font-size:13px;color:#24292f;">' +
            '<input id="openclawModelReasoningInput" type="checkbox" /> reasoning' +
            '</label>' +
            '</div>',
        focusConfirm: false,
        showCancelButton: true,
        confirmButtonText: '添加',
        cancelButtonText: '取消',
        preConfirm: function() {
            const pEl = document.getElementById('openclawModelProviderInput');
            const idEl = document.getElementById('openclawModelIdInput');
            const nEl = document.getElementById('openclawModelNameInput');
            const rEl = document.getElementById('openclawModelReasoningInput');
            const provider = (pEl && pEl.value ? pEl.value : '').trim() || 'default';
            const modelId = (idEl && idEl.value ? idEl.value : '').trim();
            const name = (nEl && nEl.value ? nEl.value : '').trim();
            const reasoning = !!(rEl && rEl.checked);
            if (!modelId) {
                window.SwalGitHub.showValidationMessage('请输入 Model ID');
                return false;
            }
            return { provider: provider, id: modelId, name: name, reasoning: reasoning };
        }
    }).then(function(res) {
        if (!res || !res.isConfirmed || !res.value) return;
        fetch('/api/openclaw/models/add', {
            method: 'POST',
            headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
            body: JSON.stringify(res.value)
        })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (!data || !data.success) {
                    const msg = (data && data.error && data.error.message) ? data.error.message : '添加失败';
                    alert(msg);
                    return;
                }
                if (typeof window.loadOpenclawModels === 'function') window.loadOpenclawModels();
            })
            .catch(function(err) {
                console.error(err);
                alert('添加失败');
            });
    });
};
window.openOpenclawModal = function() {
    if (typeof window.openBotModal === 'function') {
        window.openBotModal();
        if (typeof window.switchBotTab === 'function') window.switchBotTab('config');
        return;
    }
    Drawer.open('openclawModal');
    loadOpenclawConfig();
};

// ========== OpenClaw Cron 管理函数 ==========
window.loadCronJobList = function() {
    const container = document.getElementById('cronJobList');
    if (!container) return;
    
    function formatAtToBeijing(atValue) {
        const raw = (atValue === null || atValue === undefined) ? '' : String(atValue).trim();
        if (!raw) return '-';
        const d = new Date(raw);
        if (!Number.isNaN(d.getTime())) {
            return d.toLocaleString('zh-CN', {
                timeZone: 'Asia/Shanghai',
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            });
        }
        return raw;
    }

    fetch('/api/openclaw/cron/list', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            let jobs = [];
            if (payload && Array.isArray(payload.jobs)) {
                jobs = payload.jobs;
            } else if (Array.isArray(payload)) {
                jobs = payload;
            }
            if (jobs.length === 0) {
                container.innerHTML = '<div style="padding:20px;text-align:center;color:#666;">暂无定时任务<br><span style="font-size:11px;color:#999;">点击上方"+ 添加"创建新任务</span></div>';
                return;
            }
    
            let html = '';
            window.__openclawCronJobs = jobs;
            jobs.forEach(function(job, idx) {
                const nextRun = job.nextRunAtMs ? new Date(job.nextRunAtMs).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }) : '-';
                const statusIcon = job.enabled ? '🟢' : '🔴';
                const statusText = job.enabled ? '已启用' : '已禁用';
                const scheduleText = job.schedule && job.schedule.kind === 'cron'
                    ? job.schedule.cron
                    : (job.schedule && job.schedule.kind === 'at'
                        ? ('一次性: ' + formatAtToBeijing(job.schedule.at))
                        : '周期任务');
        
                html += '<div style="padding:10px 12px;' + (idx < jobs.length - 1 ? 'border-bottom:1px solid #eee;' : '') + '">';
                html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;gap:10px;">';
                html += '<span style="font-weight:500;font-size:14px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + escapeHtml(job.name || '未命名') + '</span>';
                html += '<span style="display:flex;align-items:center;gap:8px;flex-shrink:0;">';
                html += '<span style="font-size:11px;">' + statusIcon + ' ' + statusText + '</span>';
                html += '<button onclick="openCronEditModal(' + idx + ')" style="padding:4px 10px;border:1px solid #d0d7de;border-radius:6px;background:#fff;color:#24292f;cursor:pointer;font-size:12px;">✏️ 编辑</button>';
                html += '</span>';
                html += '</div>';
                html += '<div style="font-size:12px;color:#57606a;margin-bottom:4px;">北京时间: ' + escapeHtml(nextRun) + '</div>';
                html += '<div style="font-size:11px;color:#666;">' + escapeHtml(scheduleText) + '</div>';
                html += '</div>';
            });
    
            container.innerHTML = html;
        })
        .catch(function() {
            container.innerHTML = '<div style="padding:20px;text-align:center;color:#cf222e;">加载失败</div>';
        });
};

window.removeCronJob = function(jobId) {
    if (!confirm('确定删除这个定时任务吗？')) return;
    fetch('/api/openclaw/cron/remove', {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
        body: JSON.stringify({ jobId: jobId })
    })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (payload !== null) {
                loadCronJobList();
            }
        });
};

window.openCronAddModal = function() {
    window.openCronJobModal({ mode: 'add' });
};

window.openCronEditModal = function(jobIndex) {
    window.openCronJobModal({ mode: 'edit', jobIndex: jobIndex });
};

window.openCronJobModal = function(opts) {
    const mode = (opts && opts.mode) ? opts.mode : 'add';
    const jobIndex = opts && typeof opts.jobIndex === 'number' ? opts.jobIndex : -1;
    const job = (mode === 'edit' && Array.isArray(window.__openclawCronJobs)) ? window.__openclawCronJobs[jobIndex] : null;

    // 创建模态框
    const overlay = document.createElement('div');
    overlay.id = 'cronAddModal';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:20000;display:flex;align-items:center;justify-content:center;';
    
    const container = document.createElement('div');
    container.style.cssText = 'background:#fff;border-radius:12px;width:90%;max-width:380px;max-height:90vh;overflow:auto;';
    
    let html = `
        <div style="padding:16px 20px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;">
            <span style="font-weight:600;font-size:16px;">⏰ ${mode === 'edit' ? '编辑定时任务' : '添加定时任务'}</span>
            <button onclick="document.getElementById('cronAddModal').remove()" style="border:none;background:none;font-size:22px;cursor:pointer;color:#666;">&times;</button>
        </div>
        <div style="padding:16px 20px;">
            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:13px;color:#666;margin-bottom:6px;">提醒内容</label>
                <input type="text" id="cronMessage" placeholder="如: 喝水时间到！" style="width:100%;padding:10px 12px;border:1px solid #d0d7de;border-radius:6px;font-size:14px;box-sizing:border-box;">
            </div>
            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:13px;color:#666;margin-bottom:6px;">执行方式</label>
                <select id="cronTimeType" style="width:100%;padding:10px 12px;border:1px solid #d0d7de;border-radius:6px;font-size:14px;background:#fff;box-sizing:border-box;">
                    <option value="at">一次性 (如: 10分钟后)</option>
                    <option value="cron">周期任务 (如: 每天早上8点)</option>
                </select>
            </div>
            <div style="margin-bottom:14px;" id="cronAtGroup">
                <label style="display:block;font-size:13px;color:#666;margin-bottom:6px;">延迟时间</label>
                <select id="cronAt" style="width:100%;padding:10px 12px;border:1px solid #d0d7de;border-radius:6px;font-size:14px;background:#fff;box-sizing:border-box;">
                    <option value="5m">5 分钟后</option>
                    <option value="10m">10 分钟后</option>
                    <option value="30m">30 分钟后</option>
                    <option value="1h">1 小时后</option>
                    <option value="2h">2 小时后</option>
                    <option value="3h">3 小时后</option>
                    <option value="tomorrow">明天同时间</option>
                </select>
            </div>
            <div style="margin-bottom:14px;display:none;" id="cronCronGroup">
                <label style="display:block;font-size:13px;color:#666;margin-bottom:6px;">Cron 表达式</label>
                <select id="cronCronPreset" onchange="document.getElementById('cronCron').value=this.value" style="width:100%;padding:10px 12px;border:1px solid #d0d7de;border-radius:6px;font-size:14px;background:#fff;margin-bottom:8px;box-sizing:border-box;">
                    <option value="">-- 常用模板 --</option>
                    <option value="0 8 * * *">每天早上 8 点</option>
                    <option value="0 12 * * *">每天中午 12 点</option>
                    <option value="0 18 * * *">每天下午 6 点</option>
                    <option value="0 9 * * 1-5">工作日早上 9 点</option>
                    <option value="0 10 * * 0,6">周末早上 10 点</option>
                </select>
                <input type="text" id="cronCron" placeholder="0 8 * * *" style="width:100%;padding:10px 12px;border:1px solid #d0d7de;border-radius:6px;font-size:14px;box-sizing:border-box;">
            </div>
            <div style="display:flex;gap:10px;margin-top:20px;">
                <button id="cronCancelBtn" style="flex:1;padding:12px;border:1px solid #d0d7de;border-radius:6px;background:#fff;font-size:14px;cursor:pointer;">取消</button>
                ${mode === 'edit' ? '<button id="cronDeleteBtn" style="flex:1;padding:12px;border:1px solid #cf222e;border-radius:6px;background:#fff;color:#cf222e;font-size:14px;cursor:pointer;">删除</button>' : ''}
                <button id="cronSubmitBtn" style="flex:1;padding:12px;border:none;border-radius:6px;background:#0969da;color:#fff;font-size:14px;cursor:pointer;">${mode === 'edit' ? '保存' : '添加'}</button>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    overlay.appendChild(container);
    document.body.appendChild(overlay);

    function toastOk(text) {
        const toast = document.createElement('div');
        toast.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#2da44e;color:#fff;padding:10px 20px;border-radius:6px;font-size:14px;z-index:30000;';
        toast.textContent = text;
        document.body.appendChild(toast);
        setTimeout(function() { toast.remove(); }, 2000);
    }

    function close() {
        const el = document.getElementById('cronAddModal');
        if (el) el.remove();
    }

    function toggleInputs() {
        const type = document.getElementById('cronTimeType').value;
        const atGroup = document.getElementById('cronAtGroup');
        const cronGroup = document.getElementById('cronCronGroup');
        if (atGroup) atGroup.style.display = type === 'at' ? 'block' : 'none';
        if (cronGroup) cronGroup.style.display = type === 'cron' ? 'block' : 'none';
    }

    const timeTypeEl = document.getElementById('cronTimeType');
    if (timeTypeEl) timeTypeEl.addEventListener('change', toggleInputs);
    toggleInputs();

    const cancelBtn = document.getElementById('cronCancelBtn');
    if (cancelBtn) cancelBtn.addEventListener('click', close);

    if (job && mode === 'edit') {
        const msg = (job.name || job.message || '').replace(/^🔔\s*/g, '').trim();
        const msgEl = document.getElementById('cronMessage');
        if (msgEl) msgEl.value = msg;

        const sch = job.schedule || {};
        if (sch.kind === 'cron') {
            if (timeTypeEl) timeTypeEl.value = 'cron';
            toggleInputs();
            const cronEl = document.getElementById('cronCron');
            if (cronEl) cronEl.value = sch.cron || '';
        } else if (sch.kind === 'at') {
            if (timeTypeEl) timeTypeEl.value = 'at';
            toggleInputs();
            const atEl = document.getElementById('cronAt');
            if (atEl && sch.at) {
                const target = String(sch.at);
                const existing = Array.prototype.slice.call(atEl.options || []).some(function(o) { return o && o.value === target; });
                if (!existing) {
                    const opt = document.createElement('option');
                    opt.value = target;
                    opt.textContent = target;
                    atEl.appendChild(opt);
                }
                atEl.value = target;
            }
        }

        const delBtn = document.getElementById('cronDeleteBtn');
        if (delBtn) {
            delBtn.addEventListener('click', function() {
                if (!job || !job.id) return;
                if (!confirm('确定删除这个定时任务吗？')) return;
                fetch('/api/openclaw/cron/remove', {
                    method: 'POST',
                    headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
                    body: JSON.stringify({ jobId: job.id })
                })
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        const payload = apiData(data);
                        if (payload !== null) {
                            close();
                            loadCronJobList();
                            toastOk('✅ 已删除');
                        } else {
                            alert('删除失败: ' + ((data && (data.message || data.error)) || '未知错误'));
                        }
                    })
                    .catch(function(err) { alert('删除失败: ' + err.message); });
            });
        }
    }

    const submitBtn = document.getElementById('cronSubmitBtn');
    if (submitBtn) {
        submitBtn.addEventListener('click', function() {
            const message = (document.getElementById('cronMessage').value || '').trim();
            const timeType = document.getElementById('cronTimeType').value;

            if (!message) {
                alert('请输入提醒内容');
                return;
            }

            let schedule = '';
            if (timeType === 'at') {
                schedule = document.getElementById('cronAt').value;
            } else {
                schedule = (document.getElementById('cronCron').value || '').trim();
                if (!schedule) {
                    alert('请输入 Cron 表达式');
                    return;
                }
            }

            function doAdd() {
                return fetch('/api/openclaw/cron/add', {
                    method: 'POST',
                    headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
                    body: JSON.stringify({ message: message, timeType: timeType, schedule: schedule })
                })
                    .then(function(r) { return r.json(); });
            }

            function doRemove() {
                if (!job || !job.id) return Promise.resolve({ success: true, data: {} });
                return fetch('/api/openclaw/cron/remove', {
                    method: 'POST',
                    headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
                    body: JSON.stringify({ jobId: job.id })
                })
                    .then(function(r) { return r.json(); });
            }

            const chain = (mode === 'edit') ? doRemove().then(function(res) {
                const payload = apiData(res);
                if (payload === null) throw new Error('删除旧任务失败');
                return doAdd();
            }) : doAdd();

            chain
                .then(function(res) {
                    const payload = apiData(res);
                    if (payload !== null) {
                        close();
                        loadCronJobList();
                        toastOk(mode === 'edit' ? '✅ 已保存' : '✅ 添加成功');
                        return;
                    }
                    alert((mode === 'edit' ? '保存' : '添加') + '失败: ' + ((res && (res.message || res.error)) || '未知错误'));
                })
                .catch(function(err) {
                    alert((mode === 'edit' ? '保存' : '添加') + '失败: ' + err.message);
                });
        });
    }
};

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
            const svcName = escapeHtml(String((svc.id || 'mihomo.service')));
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
    SwalConfirm('确认操作', '确定要' + actions[action] + ' mihomo 服务吗？', function() {
        __postJson('/api/clash/control', { action: action })
            .then(function(data) {
                if (data && data.success) {
                    showToast('mihomo 服务已' + actions[action], 'success');
                    window.clashRefreshStatus();
                    return;
                }
                SwalAlert('操作失败', actions[action] + '失败: ' + ((data && (data.message || data.error)) || '未知错误'), 'error');
            })
            .catch(function(err) { showToast('请求失败: ' + err.message, 'error'); });
    }, 'warning');
};

window.openClashModal = function() { Drawer.open('clashModal'); };
window.closeClashModal = function() { Drawer.close('clashModal'); };

// FRP管理
window.loadFrpConfig = function() {
    window.refreshServiceInstallState('frp');
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
    SwalConfirm('确认操作', '确定要' + actions[action] + ' FRP 服务吗？', function() { toggleFrp(action); }, 'warning'); return;
    
    __postJson('/api/frp/control', { action: action })
        .then(function(data) {
            if (data && data.success) {
                SwalAlert('操作成功', 'FRP 服务已' + actions[action], 'success');
                window.frpcRefreshStatus();
                return;
            }
            SwalAlert('操作失败', actions[action] + '失败: ' + ((data && (data.message || data.error)) || '未知错误'), 'error');
        })
        .catch(function(err) { showToast('请求失败: ' + err.message, 'error'); });
};

window.openFrpModal = function() { Drawer.open('frpModal'); };
window.closeFrpModal = function() { Drawer.close('frpModal'); };

window.openFrpInEditor = function() {
    window.open('/json/editor?path=/usr/local/frp/frpc.toml', '_blank', 'noopener');
};

window.openClashInEditor = function() {
    const win = window.open('', '_blank');
    if (!win) { SwalAlert('提示', '弹窗被浏览器拦截，请允许弹窗后重试', 'warning'); return; }

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
        'reloadBtn.addEventListener("click",function(){if(dirty&&!confirm("confirm text"))return;load();});',
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
    SwalPrompt('代理配置', '请输入代理名称', '', function(value) { name = value; });
    if (!name) return;
    SwalPrompt('代理配置', '请输入本地端口', '', function(value) { localPort = value; });
    if (!localPort) return;
    SwalPrompt('代理配置', '请输入远程端口', '', function(value) { remotePort = value; });
    if (!remotePort) return;
    
    SwalAlert('请在编辑器中手动添加代理配置:\n\n[[proxies]]\nname = "' + name + '"\ntype = "tcp"\nlocalIP = "127.0.0.1"\nlocalPort = ' + localPort + '\nremotePort = ' + remotePort);
    window.openFrpInEditor();
};

// ============ Enhanced Clash Management ============
window.loadClashConfigEnhanced = function() {
    window.refreshServiceInstallState('clash');
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
        const proxyProviders = proxyPayload.proxy_providers || [];
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
        html += '<span style="font-weight:500;">' + (svc.id || 'mihomo.service') + '</span>';
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
        
        // 订阅管理 (proxy-providers)
        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">📡 订阅 Providers</div>';
        html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
        
        // 已有的 providers 列表
        if (proxyProviders.length > 0) {
            proxyProviders.forEach(function(provider, idx) {
                html += '<div style="padding:10px 12px;' + (idx < proxyProviders.length - 1 ? 'border-bottom:1px solid #eee;' : '') + '">';
                html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">';
                html += '<span style="font-weight:500;font-size:13px;">' + escapeHtml(provider.name || '未命名') + '</span>';
                html += '<div style="display:flex;gap:4px;">';
                html += '<button onclick="clashRefreshProvider(\'' + escapeHtml(provider.name).replace(/'/g, "\\'") + '\')" style="padding:4px 8px;border-radius:4px;border:1px solid #d0d7de;background:#fff;cursor:pointer;font-size:11px;">🔄</button>';
                html += '<button onclick="clashDeleteProvider(\'' + escapeHtml(provider.name).replace(/'/g, "\\'") + '\')" style="padding:4px 8px;border-radius:4px;border:1px solid #cf222e;background:#fff;cursor:pointer;font-size:11px;color:#cf222e;">🗑</button>';
                html += '</div></div>';
                if (provider.url) {
                    html += '<div style="font-size:11px;color:#666;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + escapeHtml(provider.url) + '</div>';
                }
                html += '</div>';
            });
        } else {
            html += '<div style="padding:20px;text-align:center;color:#666;font-size:13px;">暂无订阅</div>';
        }
        
        // 添加新订阅表单
        html += '<div style="padding:12px;border-top:1px solid #eee;">';
        html += '<input type="text" id="clashProviderUrl" placeholder="输入订阅URL" style="width:100%;padding:8px;border:1px solid #d0d7de;border-radius:6px;font-size:13px;margin-bottom:8px;box-sizing:border-box;">';
        html += '<input type="text" id="clashProviderName" placeholder="订阅名称（可选）" style="width:100%;padding:8px;border:1px solid #d0d7de;border-radius:6px;font-size:13px;margin-bottom:8px;box-sizing:border-box;">';
        html += '<div style="display:flex;gap:8px;">';
        html += '<button onclick="clashAddProvider()" style="flex:1;padding:8px;border-radius:6px;border:1px solid #2da44e;background:#2da44e;color:#fff;cursor:pointer;font-size:13px;">➕ 添加订阅</button>';
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
    if (!url) { SwalAlert('提示', '请输入订阅URL', 'warning'); return; }
    SwalConfirm('更新订阅', '更新订阅会合并新节点到现有配置，是否继续？', function() { updateSubscription(); }, 'warning');
    
    __postJson('/api/clash/subscribe', { url: url })
        .then(function(data) {
            if (data && data.success) {
                SwalAlert('更新成功', '订阅更新成功！请重启 mihomo 服务使配置生效。', 'success');
                window.loadClashConfigEnhanced();
            } else {
                SwalAlert('更新失败', '更新失败: ' + ((data && (data.message || data.error)) || '未知错误'), 'error');
            }
        })
        .catch(function(err) { showToast('请求失败: ' + err.message, 'error'); });
};

window.clashAddProvider = function() {
    const urlInput = document.getElementById('clashProviderUrl');
    const nameInput = document.getElementById('clashProviderName');
    const url = urlInput ? urlInput.value.trim() : '';
    const name = nameInput ? nameInput.value.trim() : '';
    
    if (!url) { SwalAlert('提示', '请输入订阅URL', 'warning'); return; }
    
    __postJson('/api/clash/provider/add', { url: url, name: name })
        .then(function(data) {
            if (data && data.success) {
                SwalAlert('添加成功', '订阅添加成功！请重启 mihomo 服务使配置生效。', 'success');
                window.loadClashConfigEnhanced();
            } else {
                SwalAlert('添加失败', '添加失败: ' + ((data && (data.message || data.error)) || '未知错误'), 'error');
            }
        })
        .catch(function(err) { showToast('请求失败: ' + err.message, 'error'); });
};

window.clashDeleteProvider = function(name) {
    SwalConfirm('删除订阅', '确定要删除订阅 "' + name + '" 吗？', function() {
        __postJson('/api/clash/provider/delete', { name: name })
            .then(function(data) {
                if (data && data.success) {
                    SwalAlert('删除成功', '订阅删除成功！请重启 mihomo 服务使配置生效。', 'success');
                    window.loadClashConfigEnhanced();
                } else {
                    SwalAlert('删除失败', '删除失败: ' + ((data && (data.message || data.error)) || '未知错误'), 'error');
                }
            })
            .catch(function(err) { showToast('请求失败: ' + err.message, 'error'); });
    }, 'warning');
};

window.clashRefreshProvider = function(name) {
    showToast('正在刷新订阅...', 'info');
    __postJson('/api/clash/provider/refresh', { name: name })
        .then(function(data) {
            if (data && data.success) {
                SwalAlert('刷新成功', '订阅 "' + name + '" 刷新成功！', 'success');
                window.loadClashConfigEnhanced();
            } else {
                SwalAlert('刷新失败', '刷新失败: ' + ((data && (data.message || data.error)) || '未知错误'), 'error');
            }
        })
        .catch(function(err) { showToast('请求失败: ' + err.message, 'error'); });
};

window.clashOpenProxyList = function(groupName) {
    fetch('/api/clash/proxies', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            const proxies = payload ? (payload.proxies || []) : [];
            if (proxies.length === 0) { SwalAlert('提示', '暂无数控节点', 'warning'); return; }
            
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
        .catch(function(err) { SwalAlert('加载失败', '加载节点失败: ' + err.message, 'error'); });
};

window.clashSwitchProxy = function(groupName, proxyName) {
    SwalConfirm('切换代理', '将 ' + groupName + ' 切换到 ' + proxyName + '？', function() { switchProxy(groupName, proxyName); }, 'warning'); return;
    __postJson('/api/clash/switch', { group: groupName, proxy: proxyName })
        .then(function(data) {
            if (data && data.success) {
                SwalAlert('切换成功', '请重启 mihomo 服务使配置生效', 'success');
                window.loadClashConfigEnhanced();
            } else {
                SwalAlert('切换失败', '切换失败: ' + ((data && (data.message || data.error)) || '未知错误'), 'error');
            }
        })
        .catch(function(err) { showToast('请求失败: ' + err.message, 'error'); });
};

// 覆盖原来的打开函数
window.openClashModalOriginal = window.openClashModal;
window.openClashModal = function() { Drawer.open('clashModal'); };
