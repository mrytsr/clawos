// ============ 文件浏览器模块 ============
/* global Drawer, showToast, refreshFileList, escapeHtml, performRename, performMove, performDelete, copyFilePath, copyDownloadUrl, downloadFile, addToChat, openTerminal */
// 注意：currentItemPath, currentItemName, currentItemIsDir 由 globals.js 定义

// 文件菜单
function showMenuModal(path, name, isDir) {
    window.currentItemPath = path;
    window.currentItemName = name;
    window.currentItemIsDir = isDir;
    document.getElementById('menuTitle').textContent = name;
    Drawer.open('menuModal');
}

function closeMenuModal() {
    Drawer.close('menuModal');
}

function closeMenuOnBackdrop(event) {
    if (event.target.id === 'menuModal') {
        closeMenuModal();
    }
}

// 拖拽相关变量和函数（使用 window 对象）
function startDrag(e) {
    window.isDragging = true;
    window.startY = e.clientY || e.touches[0].clientY;
    const sheet = e.target.closest('.bottom-sheet');
    window.startHeight = sheet ? sheet.offsetHeight : 300;
    document.addEventListener('mousemove', onDrag);
    document.addEventListener('mouseup', endDrag);
    document.addEventListener('touchmove', onDrag);
    document.addEventListener('touchend', endDrag);
}

function onDrag(e) {
    if (!window.isDragging) { return; }
    const currentY = e.clientY || e.touches[0].clientY;
    const delta = window.startY - currentY;
    const sheet = document.querySelector('.bottom-sheet[style*="display: block"]') || document.querySelector('.bottom-sheet');
    if (sheet) {
        const newHeight = Math.max(200, Math.min(window.innerHeight * 0.9, window.startHeight + delta));
        sheet.style.height = newHeight + 'px';
    }
}

function endDrag() {
    window.isDragging = false;
    document.removeEventListener('mousemove', onDrag);
    document.removeEventListener('mouseup', endDrag);
    document.removeEventListener('touchmove', onDrag);
    document.removeEventListener('touchend', endDrag);
}

// 文件操作
function handleMenuAction(action) {
    closeMenuModal();
    setTimeout(() => {
        switch(action) {
            case 'download': downloadFile(window.currentItemPath); break;
            case 'copyUrl': copyDownloadUrl(window.currentItemPath); break;
            case 'copyPath': copyFilePath(window.currentItemPath); break;
            case 'rename': showRenameModal(); break;
            case 'move': showMoveModal(); break;
            case 'clone': cloneItem(); break;
            case 'cut':
                if (window.Clipboard && typeof window.Clipboard.set === 'function') {
                    window.Clipboard.set('cut', { path: window.currentItemPath, name: window.currentItemName, isDir: window.currentItemIsDir });
                    showToast('已剪切', 'success');
                }
                break;
            case 'copy':
                if (window.Clipboard && typeof window.Clipboard.set === 'function') {
                    window.Clipboard.set('copy', { path: window.currentItemPath, name: window.currentItemName, isDir: window.currentItemIsDir });
                    showToast('已复制', 'success');
                }
                break;
            case 'chat': addToChat(window.currentItemPath); break;
            case 'terminal': openTerminal(window.currentItemPath, window.currentItemIsDir); break;
            case 'delete': confirmDelete(window.currentItemPath, window.currentItemName); break;
            case 'details': showDetails(window.currentItemPath, window.currentItemName); break;
        }
    }, 50);
}

// 删除
function confirmDelete(path, name) {
    if (window.showConfirmDrawer) {
        window.showConfirmDrawer(
            '删除',
            '确定要删除 "' + (name || '') + '" 吗？',
            '删除',
            function() { performDelete(path); },
            true
        );
        return;
    }
    document.getElementById('itemNameToDelete').textContent = name;
    Drawer.open('confirmModal');
}

function closeConfirmModal() {
    Drawer.close('confirmModal');
}

function performDelete(path) {
    var p = typeof path === 'string' && path ? path : window.currentItemPath;
    fetch(`/delete/${encodeURIComponent(p)}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showToast('已移到回收站', 'success');
                refreshFileList();
            } else {
                showToast(data.message || '删除失败', 'error');
            }
        })
        .catch(() => showToast('删除失败', 'error'));
    if (document.getElementById('confirmModal') && document.getElementById('confirmModal').classList.contains('open')) {
        closeConfirmModal();
    }
}

// 重命名
function showRenameModal() {
    Drawer.open('renameModal');
    document.getElementById('renameInput').value = window.currentItemName;
    setTimeout(() => document.getElementById('renameInput').focus(), 100);
}

function closeRenameModal() {
    Drawer.close('renameModal');
}

function closeRenameOnBackdrop(event) {
    if (event.target.id === 'renameModal') {
        closeRenameModal();
    }
}

function performRename() {
    const newName = document.getElementById('renameInput').value.trim();
    if (!newName) { return; }
    
    fetch(`/rename/${encodeURIComponent(window.currentItemPath)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast('重命名成功', 'success');
            refreshFileList();
        } else {
            showToast(data.message || '重命名失败', 'error');
        }
    })
    .catch(() => showToast('重命名失败', 'error'));
    
    closeRenameModal();
}

// 移动
function showMoveModal() {
    Drawer.open('moveModal');
    document.getElementById('targetPathInput').value = '';
}

function closeMoveModal() {
    Drawer.close('moveModal');
}

function performMove() {
    const targetPath = document.getElementById('targetPathInput').value.trim();
    if (!targetPath) { return; }
    
    fetch(`/move/${encodeURIComponent(window.currentItemPath)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_path: targetPath })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast('移动成功', 'success');
            refreshFileList();
        } else {
            showToast(data.message || '移动失败', 'error');
        }
    })
    .catch(() => showToast('移动失败', 'error'));
    
    closeMoveModal();
}

// 克隆
function cloneItem() {
    fetch(`/clone/${encodeURIComponent(window.currentItemPath)}`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showToast(data.message, 'success');
                refreshFileList();
            } else {
                showToast(data.message || '克隆失败', 'error');
            }
        })
        .catch(() => showToast('克隆失败', 'error'));
}

// 下载
function downloadFile(path) {
    window.location.href = `/download/${encodeURIComponent(path)}`;
}

function copyDownloadUrl(path) {
    const url = window.location.origin + '/download/' + encodeURIComponent(path);
    copyToClipboard(url);
}

function copyFilePath(path) {
    copyToClipboard(path);
}

// 通用复制函数
function copyToClipboard(text) {
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
        showToast(successful ? '复制成功' : '复制失败', successful ? 'success' : 'error');
    } catch (err) {
        document.body.removeChild(textarea);
        showToast('复制失败', 'error');
    }
}

function editFile(path) {
    window.location.href = `/edit/${encodeURIComponent(path)}`;
}

// 添加到对话
function addToChat(path) {
    if (typeof window.openBotModal === 'function') {
        window.openBotModal();
    }
    const input = document.getElementById('botInput');
    if (input) {
        const prefix = path ? (path + '： ') : '';
        input.value = (input.value || '') + prefix;
        input.focus();
        try { input.setSelectionRange(input.value.length, input.value.length); } catch (e) {}
    }
}

// 详情
window.showDetails = function(path, name) {
    const modal = document.getElementById('detailsModal');
    const content = document.getElementById('detailsContent');
    if (modal) { Drawer.open('detailsModal'); }
    if (content) { content.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>'; }
    
    fetch('/api/file/info?path=' + encodeURIComponent(path))
        .then(r => r.json())
        .then(data => {
            if (data && data.success && content) {
                const info = data.data;
                content.innerHTML = `
                    <div style="padding: 16px 0;">
                        <div style="font-size: 18px; font-weight: bold; margin-bottom: 16px; word-break: break-all;">${escapeHtml(name)}</div>
                        <table style="width:100%;border-collapse:collapse;font-size:14px;">
                            <tr style="border-bottom:1px solid #eee;"><td style="padding:10px;color:#666;">路径</td><td style="padding:10px;font-family:monospace;word-break:break-all;">${escapeHtml(path)}</td></tr>
                            <tr style="border-bottom:1px solid #eee;"><td style="padding:10px;color:#666;">类型</td><td style="padding:10px;">${info.is_dir ? '📁 文件夹' : '📄 文件'}</td></tr>
                            <tr style="border-bottom:1px solid #eee;"><td style="padding:10px;color:#666;">大小</td><td style="padding:10px;">${info.size_human || formatSize(info.size)}</td></tr>
                            <tr style="border-bottom:1px solid #eee;"><td style="padding:10px;color:#666;">权限</td><td style="padding:10px;font-family:monospace;">${info.permissions || '未知'}</td></tr>
                            <tr style="border-bottom:1px solid #eee;"><td style="padding:10px;color:#666;">所有者</td><td style="padding:10px;">${info.owner || '未知'}</td></tr>
                            <tr style="border-bottom:1px solid #eee;"><td style="padding:10px;color:#666;">创建时间</td><td style="padding:10px;">${info.ctime || '未知'}</td></tr>
                            <tr style="border-bottom:1px solid #eee;"><td style="padding:10px;color:#666;">修改时间</td><td style="padding:10px;">${info.mtime || '未知'}</td></tr>
                            <tr style="border-bottom:1px solid #eee;"><td style="padding:10px;color:#666;">访问时间</td><td style="padding:10px;">${info.atime || '未知'}</td></tr>
                        </table>
                    </div>
                `;
            } else if (content) {
                const msg = data && data.error && data.error.message ? data.error.message : '❌ 获取详情失败';
                content.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">' + escapeHtml(msg) + '</div>';
            }
        })
        .catch(() => {
            if (content) { content.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">❌ 获取详情失败</div>'; }
        });
};

window.closeDetailsModal = function() {
    Drawer.close('detailsModal');
};

window.closeDetailsOnBackdrop = function(event) {
    if (event.target.id === 'detailsModal') { closeDetailsModal(); } };

function refreshFileList() {
    window.location.reload();
}

function formatSize(size) {
    if (size < 1024) { return size + ' B'; }
    if (size < 1024 * 1024) { return (size / 1024).toFixed(1) + ' KB'; }
    if (size < 1024 * 1024 * 1024) { return (size / 1024 / 1024).toFixed(1) + ' MB'; }
    return (size / 1024 / 1024 / 1024).toFixed(1) + ' GB';
}

// 导出到 window
window.showMenuModal = showMenuModal;
window.closeMenuModal = closeMenuModal;
window.closeMenuOnBackdrop = closeMenuOnBackdrop;
window.startDrag = startDrag;
window.handleMenuAction = handleMenuAction;
window.confirmDelete = confirmDelete;
window.closeConfirmModal = closeConfirmModal;
window.performDelete = performDelete;
window.showRenameModal = showRenameModal;
window.closeRenameModal = closeRenameModal;
window.closeRenameOnBackdrop = closeRenameOnBackdrop;
window.performRename = performRename;
window.showMoveModal = showMoveModal;
window.closeMoveModal = closeMoveModal;
window.performMove = performMove;
window.cloneItem = cloneItem;
window.downloadFile = downloadFile;
window.copyDownloadUrl = copyDownloadUrl;
window.copyFilePath = copyFilePath;
window.editFile = editFile;
window.addToChat = addToChat;
window.refreshFileList = refreshFileList;
