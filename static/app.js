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
    'network': { modal: 'networkModal', load: 'loadNetworkList', open: 'openNetworkModal' }
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
            if (data.results && data.results.length > 0) {
                resultsContainer.innerHTML = data.results.map(item => 
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

// 执行操作
function performDelete() {
    fetch(`/delete/${encodeURIComponent(currentItemPath)}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) { showToast('已移到回收站', 'success'); refreshFileList(); }
            else { showToast(data.message || '删除失败', 'error'); }
        })
        .catch(() => showToast('删除失败', 'error'));
    closeConfirmModal();
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
    // 文件列表项点击
    document.querySelectorAll('.file-item').forEach(item => {
        item.addEventListener('click', function(e) {
            if (!e.target.closest('.menu-btn') && !e.target.closest('.checkbox-wrapper') && !e.target.closest('input[type="checkbox"]')) {
                const path = this.dataset.path;
                const isDir = this.dataset.isDir === 'true';
                if (isDir) {
                    window.location.href = '/browse/' + encodeURIComponent(path);
                } else {
                    // 点击文件直接打开，而不是预览
                    window.location.href = '/view/' + encodeURIComponent(path);
                }
            }
        });
    });
    // 菜单项点击
    document.getElementById('mainMenuDrawer')?.addEventListener('click', function(e) {
        const menuItem = e.target.closest('.menu-item[data-action]');
        if (menuItem) handleMainMenu(menuItem.dataset.action);
    });
});
