// ============ 6002_clawos 主入口 ============
// 全局函数已由 js/globals.js 预加载
// 此文件只包含 action 映射和 API 调用

// action 到 modal ID 和加载函数的映射（供 globals.js 中的 handleMainMenu 使用）
window.actionToModalMap = {
    'git': { modal: 'gitModal', load: 'loadGitList', open: 'openGitModal' },
    'process': { modal: 'processModal', load: 'loadProcessList', open: 'openProcessModal' },
    'system-package': { modal: 'systemPackageModal', load: 'loadSystemPackageList', open: 'openSystemPackageModal' },
    'pip': { modal: 'pipModal', load: 'loadPipList', open: 'openPipModal' },
    'npm': { modal: 'npmModal', load: 'loadNpmList', open: 'openNpmModal' },
    'docker': { modal: 'dockerModal', load: 'loadDockerTabs', open: 'openDockerModal' },
    'systemd': { modal: 'systemdModal', load: 'loadSystemdList', open: 'openSystemdModal' },
    'disk': { modal: 'diskModal', load: 'loadDiskList', open: 'openDiskModal' },
    'network': { modal: 'networkModal', load: 'loadNetworkList', open: 'openNetworkModal' },
    'gpu': { modal: 'gpuModal', load: 'loadGpuInfo', open: 'openGpuModal' },
    'ollama': { modal: 'ollamaModal', load: 'loadOllamaModels', open: 'openOllamaModal' },
    'openclaw': { modal: 'openclawModal', load: 'loadOpenclawConfig', open: 'openOpenclawModal' }
};

// 搜索功能
function doSearch() {
    const keyword = document.getElementById('searchInput').value.trim();
    if (!keyword) return;
    const resultsContainer = document.getElementById('searchResults');
    resultsContainer.innerHTML = '<div style="text-align:center;padding:20px;color:#666;">搜索中...</div>';
    fetch('/api/search?q=' + encodeURIComponent(keyword))
        .then(r => r.json())
        .then(data => {
            const results = data && data.success && data.data ? data.data.results : null;
            if (results && results.length > 0) {
                resultsContainer.innerHTML = results.map(item => 
                    `<div class="search-result-item" onclick="window.location.href='/browse/${item.path}'">
                        <span style="font-size:20px;margin-right:10px;">${item.icon}</span>
                        <div style="flex:1;">
                            <div style="font-weight:500;">${item.name}</div>
                            <div style="font-size:12px;color:#666;">${item.path}</div>
                        </div>
                    </div>`
                ).join('');
            } else {
                resultsContainer.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">未找到结果</div>';
            }
        })
        .catch(() => { resultsContainer.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">搜索失败</div>'; });
}

// 回收站抽屉
window.openTrashDrawer = function(callbacks) {
    Drawer.open('trashDrawer', callbacks);
    loadTrashList();
};
window.closeTrashDrawer = function(callbacks) {
    Drawer.close('trashDrawer', Object.assign({}, callbacks || {}, {
        afterClose: function() {
            const container = document.getElementById('trashListContainer');
            if (container) container.innerHTML = '';
            if (callbacks && typeof callbacks.afterClose === 'function') callbacks.afterClose();
        }
    }));
};

window.loadTrashList = function() {
    const container = document.getElementById('trashListContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/trash/list', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const items = data && data.success && data.data ? data.data.items : null;
            if (!container) return;
            if (!items || items.length === 0) {
                container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">回收站是空的</div>';
                return;
            }
            container.innerHTML = items.map(item => {
                const rawName = item.name || '';
                const rawDisplayName = item.display_name || item.name || '';
                const displayName = escapeHtml(rawDisplayName);
                const deletedAt = escapeHtml(item.deleted_at || '');
                const typeIcon = item.is_dir ? '📁' : '📄';
                return (
                    `<div style="padding:12px;border:1px solid #eee;border-radius:10px;margin-bottom:10px;background:#fff;display:flex;gap:12px;align-items:flex-start;">` +
                        `<div style="font-size:18px;line-height:1;">${typeIcon}</div>` +
                        `<div style="flex:1;min-width:0;">` +
                            `<div style="font-weight:600;word-break:break-word;white-space:pre-wrap;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">` +
                                `<span>${displayName}</span>` +
                                `<button class="modal-btn modal-btn-confirm" style="padding:4px 8px;border-radius:999px;font-size:12px;" data-trash-name="${encodeURIComponent(rawName)}" data-trash-default="${encodeURIComponent(rawDisplayName)}" onclick="restoreTrashItemFromButton(this)">还原</button>` +
                            `</div>` +
                            `<div style="margin-top:4px;color:#666;font-size:12px;">删除时间: ${deletedAt}</div>` +
                        `</div>` +
                    `</div>`
                );
            }).join('');
        })
        .catch(() => {
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败</div>';
        });
};

window.restoreTrashItemFromButton = function(btn) {
    if (!btn || !btn.dataset) return;
    const rawName = decodeURIComponent(btn.dataset.trashName || '');
    const suggested = decodeURIComponent(btn.dataset.trashDefault || '');
    showPromptDrawer(
        '还原',
        '输入还原路径（相对于根目录）',
        '例如：docs/a.txt',
        suggested,
        '还原',
        function(targetPath) {
            if (!targetPath) return;
            fetch('/api/trash/restore/' + encodeURIComponent(rawName), {
                method: 'POST',
                headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
                body: JSON.stringify({ target_path: targetPath })
            })
                .then(r => r.json())
                .then(data => {
                    if (data && data.success) {
                        showToast('还原成功', 'success');
                        loadTrashList();
                    } else {
                        showToast((data && data.error && data.error.message) || '还原失败', 'error');
                    }
                })
                .catch(() => showToast('还原失败', 'error'));
        }
    );
};

window.clearTrash = function() {
    showConfirmDrawer(
        '清空回收站',
        '确定要清空回收站吗？此操作不可恢复。',
        '清空',
        function() {
            fetch('/api/trash/clear', { method: 'POST', headers: authHeaders() })
                .then(r => r.json())
                .then(data => {
                    if (data && data.success) {
                        showToast('回收站已清空', 'success');
                        loadTrashList();
                    } else {
                        showToast((data && data.error && data.error.message) || '清空失败', 'error');
                    }
                })
                .catch(() => showToast('清空失败', 'error'));
        },
        true
    );
};

// 创建菜单抽屉（加号）
window.openCreateMenuDrawer = function(callbacks) {
    Drawer.open('createMenuDrawer', callbacks);
};
window.closeCreateMenuDrawer = function(callbacks) {
    Drawer.close('createMenuDrawer', callbacks);
};
window.createMenuUpload = function() {
    closeCreateMenuDrawer();
    const input = document.getElementById('fileInputInline');
    if (input) input.click();
};
window.createMenuNewFolder = function() {
    closeCreateMenuDrawer();
    showPromptDrawer(
        '新建文件夹',
        '请输入文件夹名称',
        '例如：assets',
        '',
        '创建',
        function(name) {
            if (!name) return;
            const currentPath = document.getElementById('currentBrowsePath') ? document.getElementById('currentBrowsePath').value : '';
            const url = currentPath ? '/mkdir/' + encodeURIComponent(currentPath) : '/mkdir';
            fetch(url, {
                method: 'POST',
                headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
                body: JSON.stringify({ name: name })
            })
                .then(r => r.json())
                .then(data => {
                    if (data && data.success) {
                        showToast('创建成功', 'success');
                        refreshFileList();
                    } else {
                        showToast((data && (data.message || (data.error && data.error.message))) || '创建失败', 'error');
                    }
                })
                .catch(() => showToast('创建失败', 'error'));
        }
    );
};
window.createMenuNewFile = function() {
    closeCreateMenuDrawer();
    showPromptDrawer(
        '新建文件',
        '请输入文件名',
        '例如：README.md',
        '',
        '创建',
        function(name) {
            if (!name) return;
            const currentPath = document.getElementById('currentBrowsePath') ? document.getElementById('currentBrowsePath').value : '';
            const url = currentPath ? '/touch/' + encodeURIComponent(currentPath) : '/touch';
            fetch(url, {
                method: 'POST',
                headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
                body: JSON.stringify({ name: name })
            })
                .then(r => r.json())
                .then(data => {
                    if (data && data.success) {
                        showToast('创建成功', 'success');
                        refreshFileList();
                    } else {
                        showToast((data && (data.message || (data.error && data.error.message))) || '创建失败', 'error');
                    }
                })
                .catch(() => showToast('创建失败', 'error'));
        }
    );
};

// 执行操作
function performDelete(path) {
    const p = (typeof path === 'string' && path) ? path : currentItemPath;
    fetch(`/delete/${encodeURIComponent(p)}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) { showToast('已移到回收站', 'success'); refreshFileList(); }
            else { showToast(data.message || '删除失败', 'error'); }
        })
        .catch(() => showToast('删除失败', 'error'));
    const m = document.getElementById('confirmModal');
    if (m && m.classList.contains('open')) closeConfirmModal();
}

function performRename() {
    const newName = document.getElementById('renameInput').value.trim();
    if (!newName) return;
    fetch(`/rename/${encodeURIComponent(currentItemPath)}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) { showToast('重命名成功', 'success'); refreshFileList(); }
        else { showToast(data.message || '重命名失败', 'error'); }
    })
    .catch(() => showToast('重命名失败', 'error'));
    closeRenameModal();
}

function performMove() {
    const targetPath = document.getElementById('targetPathInput').value.trim();
    if (!targetPath) return;
    fetch(`/move/${encodeURIComponent(currentItemPath)}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_path: targetPath })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) { showToast('移动成功', 'success'); refreshFileList(); }
        else { showToast(data.message || '移动失败', 'error'); }
    })
    .catch(() => showToast('移动失败', 'error'));
    closeMoveModal();
}

function cloneItem() {
    fetch(`/clone/${encodeURIComponent(currentItemPath)}`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) { showToast(data.message, 'success'); refreshFileList(); }
            else { showToast(data.message || '克隆失败', 'error'); }
        })
        .catch(() => showToast('克隆失败', 'error'));
}

function downloadFile(path) { window.location.href = `/download/${encodeURIComponent(path)}`; }
function copyDownloadUrl(path) { 
    const url = window.location.origin + '/download/' + encodeURIComponent(path);
    copyToClipboard(url, '复制成功');
}
function copyFilePath(path) { 
    copyToClipboard(path, '复制成功');
}

// 通用复制函数
function copyToClipboard(text, successMsg) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    textarea.style.left = '0';
    textarea.style.top = '0';
    document.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, text.length);
    try {
        const successful = document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast(successful ? successMsg : '复制失败', successful ? 'success' : 'error');
    } catch (err) {
        document.body.removeChild(textarea);
        showToast('复制失败', 'error');
    }
}
function editFile(path) { window.location.href = `/edit/${encodeURIComponent(path)}`; }
function addToChat(path) { showToast('功能开发中', 'info'); }

// 文件菜单操作
window.handleMenuAction = function(action) {
    closeMenuModal();
    setTimeout(() => {
        switch(action) {
            case 'download': downloadFile(currentItemPath); break;
            case 'copyUrl': copyDownloadUrl(currentItemPath); break;
            case 'copyPath': copyFilePath(currentItemPath); break;
            case 'rename': showRenameModal(); break;
            case 'move': showMoveModal(); break;
            case 'clone': cloneItem(); break;
            case 'cut':
                if (window.Clipboard && typeof window.Clipboard.set === 'function') {
                    window.Clipboard.set('cut', { path: currentItemPath, name: currentItemName, isDir: currentItemIsDir });
                    showToast('已剪切', 'success');
                } else {
                    showToast('剪切不可用', 'error');
                }
                break;
            case 'copy':
                if (window.Clipboard && typeof window.Clipboard.set === 'function') {
                    window.Clipboard.set('copy', { path: currentItemPath, name: currentItemName, isDir: currentItemIsDir });
                    showToast('已复制', 'success');
                } else {
                    showToast('复制不可用', 'error');
                }
                break;
            case 'chat': addToChat(currentItemPath); break;
            case 'terminal': openTerminal(currentItemPath, currentItemIsDir); break;
            case 'delete': confirmDelete(currentItemPath, currentItemName); break;
            case 'details': showDetails(currentItemPath, currentItemName); break;
        }
    }, 50);
};

// 终端处理
function handleTerminalBackdrop(event) {
    if (event.target.id === 'terminalModal') closeTerminal();
}

// 键盘快捷键
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey && e.key === 'f') || (e.key === '/' && !e.target.matches('input, textarea'))) {
        e.preventDefault();
        openSearchModal();
    }
    if (e.key === 'Escape') {
        closeSearchModal();
    }
});

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
});
