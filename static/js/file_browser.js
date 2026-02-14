// ============ 文件浏览器模块 ============
/* global Drawer, showToast, refreshFileList, escapeHtml, performRename, performMove, performDelete, copyFilePath, copyDownloadUrl, downloadFile, addToChat, openTerminal */
// 注意：currentItemPath, currentItemName, currentItemIsDir 由 globals.js 定义

// 文件菜单
function setSearchModalInteractive(enabled) {
    var m = document.getElementById('searchModal');
    var b = document.getElementById('searchBackdrop');
    var pe = enabled ? '' : 'none';
    if (m) m.style.pointerEvents = pe;
    if (b) b.style.pointerEvents = pe;
}

function setMenuTopLayer(on) {
    var modal = document.getElementById('menuModal');
    var backdrop = document.getElementById('menuBackdrop');
    if (backdrop) backdrop.style.zIndex = on ? '20009' : '';
    if (modal) modal.style.zIndex = on ? '20010' : '';
}

function clampNumber(v, min, max) {
    if (v < min) return min;
    if (v > max) return max;
    return v;
}

function positionMenuPopover(anchorRect) {
    var modal = document.getElementById('menuModal');
    if (!modal || !anchorRect) return;
    var vw = Math.max(1, window.innerWidth || document.documentElement.clientWidth || 1);
    var vh = Math.max(1, window.innerHeight || document.documentElement.clientHeight || 1);
    var pad = 12;

    modal.style.left = '0px';
    modal.style.top = '0px';
    modal.style.right = '';
    modal.style.bottom = '';

    var w = modal.offsetWidth || 280;
    var h = modal.offsetHeight || 360;

    var preferRight = (anchorRect.right || 0) - w;
    var left = clampNumber(preferRight, pad, Math.max(pad, vw - w - pad));

    var belowTop = (anchorRect.bottom || 0) + 8;
    var aboveTop = (anchorRect.top || 0) - h - 8;
    var top = belowTop;
    if (top + h + pad > vh && aboveTop >= pad) top = aboveTop;
    top = clampNumber(top, pad, Math.max(pad, vh - h - pad));

    modal.style.left = String(Math.round(left)) + 'px';
    modal.style.top = String(Math.round(top)) + 'px';
}

function showMenuModal(path, name, isDir, opts) {
    var o = opts && typeof opts === 'object' ? opts : null;
    window.currentItemPath = path;
    window.currentItemName = name;
    window.currentItemIsDir = isDir;
    document.getElementById('menuTitle').textContent = name;
    if (typeof updateMenuPinButton === 'function') updateMenuPinButton();
    var editEl = document.getElementById('menuEditItem');
    if (editEl) {
        editEl.style.display = isDir ? 'none' : '';
        editEl.onclick = function() {
            closeMenuModal();
            editFile(window.currentItemPath);
        };
    }
    var downloadEl = document.getElementById('menuDownloadItem');
    if (downloadEl) downloadEl.style.display = isDir ? 'none' : '';
    var copyUrlEl = document.getElementById('menuCopyUrlItem');
    if (copyUrlEl) copyUrlEl.style.display = isDir ? 'none' : '';
    var extractEl = document.getElementById('menuExtractItem');
    if (extractEl) extractEl.style.display = (!isDir && isArchiveName(name)) ? '' : 'none';
    var newArchiveEl = document.getElementById('menuNewArchiveItem');
    if (newArchiveEl) newArchiveEl.style.display = '';

    var menuModal = document.getElementById('menuModal');
    if (menuModal) {
        if (o && o.fromSearch) menuModal.classList.add('menu-popover');
        else menuModal.classList.remove('menu-popover');
        if (!(o && o.fromSearch)) {
            menuModal.style.left = '';
            menuModal.style.top = '';
            menuModal.style.right = '';
            menuModal.style.bottom = '';
        }
    }

    var fromSearch = !!(o && o.fromSearch);
    setMenuTopLayer(fromSearch);
    if (fromSearch) setSearchModalInteractive(false);

    Drawer.open('menuModal');

    if (fromSearch && o && o.anchorRect) {
        requestAnimationFrame(function() {
            positionMenuPopover(o.anchorRect);
        });
    }
}

function openCurrentFolderMenu(ev) {
    if (ev && typeof ev.preventDefault === 'function') ev.preventDefault();
    if (ev && typeof ev.stopPropagation === 'function') ev.stopPropagation();
    var pathEl = document.getElementById('currentBrowsePath');
    var nameEl = document.getElementById('currentBrowseName');
    var path = pathEl ? String(pathEl.value || '') : '';
    var name = nameEl ? String(nameEl.value || '') : '';
    if (!name) {
        var p = (path || '').replace(/\\/g, '/').replace(/\/+$/, '');
        name = p ? p.split('/').pop() : '根目录';
    }
    showMenuModal(path, name, true);
}

function closeMenuModal() {
    setSearchModalInteractive(true);
    setMenuTopLayer(false);
    var menuModal = document.getElementById('menuModal');
    if (menuModal) {
        menuModal.classList.remove('menu-popover');
        menuModal.style.left = '';
        menuModal.style.top = '';
        menuModal.style.right = '';
        menuModal.style.bottom = '';
    }
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
    closeMenuModal(); // 点击菜单项后关闭菜单
    setTimeout(() => {
        switch(action) {
            case 'download': downloadFile(window.currentItemPath, { name: window.currentItemName }); break;
            case 'edit': openEditor(window.currentItemPath); break;
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
            case 'extract': extractArchiveHere(window.currentItemPath, window.currentItemName); break;
            case 'newArchive':
                closeMenuModal();
                openArchiveCreateDialog([window.currentItemPath], getParentDir(window.currentItemPath));
                break;
        }
    }, 50);
}

function normalizeRelPath(path) {
    return (path || '').toString().replace(/\\/g, '/').replace(/^\/+/, '').replace(/\/+$/, '');
}

function getParentDir(path) {
    var p = normalizeRelPath(path);
    var idx = p.lastIndexOf('/');
    return idx >= 0 ? p.slice(0, idx) : '';
}

function getCurrentBrowsePath() {
    var el = document.getElementById('currentBrowsePath');
    return el ? normalizeRelPath(el.value || '') : '';
}

var __pinState = { dir: '', byName: {} };

function __pinHeaders() {
    var h = {};
    if (typeof window.authHeaders === 'function') {
        try {
            Object.assign(h, window.authHeaders() || {});
        } catch (e) {}
    }
    return h;
}

function __togglePin(dirRel, name) {
    var dir = normalizeRelPath(dirRel);
    return fetch('/api/pin/toggle', {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, __pinHeaders()),
        body: JSON.stringify({ dir: dir, name: name })
    })
        .then(function(r) { return r.json().catch(function() { return null; }); });
}

function __rebuildPinMap(pins) {
    var m = {};
    (Array.isArray(pins) ? pins : []).forEach(function(p) {
        if (!p || !p.name) return;
        var t = typeof p.pinned_at === 'number' ? p.pinned_at : parseInt(p.pinned_at, 10) || 0;
        m[String(p.name)] = t;
    });
    __pinState.byName = m;
}

function __isPinnedName(name) {
    return Object.prototype.hasOwnProperty.call(__pinState.byName, String(name));
}

function __removeInlinePinButtons() {
    document.querySelectorAll('.file-list .file-name button.pin-btn').forEach(function(btn) {
        if (btn && btn.parentNode) btn.parentNode.removeChild(btn);
    });
}

function __applyPinnedClasses() {
    document.querySelectorAll('.file-list .file-item[data-name]').forEach(function(el) {
        var name = String(el.dataset && el.dataset.name ? el.dataset.name : '');
        if (!name) return;
        if (__isPinnedName(name)) el.classList.add('is-pinned');
        else el.classList.remove('is-pinned');
    });
}

function __applyPinOrder() {
    var list = document.querySelector('.file-list');
    if (!list) return;

    var pinnedEls = [];
    document.querySelectorAll('.file-list .file-item[data-name]').forEach(function(el) {
        var name = String(el.dataset && el.dataset.name ? el.dataset.name : '');
        if (!name) return;
        if (!__isPinnedName(name)) return;
        pinnedEls.push({ el: el, name: name, t: __pinState.byName[name] || 0 });
    });

    if (!pinnedEls.length) return;

    pinnedEls.sort(function(a, b) { return (b.t || 0) - (a.t || 0); });
    var first = list.firstChild;
    pinnedEls.forEach(function(item) {
        if (item.el && item.el.parentNode === list) {
            list.insertBefore(item.el, first);
            first = item.el.nextSibling;
        }
    });
}

function __applyPinsToDom(dirRel) {
    __removeInlinePinButtons();
    __applyPinnedClasses();
    __applyPinOrder();
}

function updateMenuPinButton() {
    var btn = document.getElementById('menuPinBtn');
    if (!btn) return;

    var path = normalizeRelPath(window.currentItemPath || '');
    var name = String(window.currentItemName || '').trim();
    var isDir = !!window.currentItemIsDir;

    if (!path || !name || name === '根目录') {
        btn.style.display = 'none';
        return;
    }

    var dirRel = getParentDir(path);
    if (dirRel === path && isDir) {
        btn.style.display = 'none';
        return;
    }
    if (normalizeRelPath(dirRel) !== getCurrentBrowsePath()) {
        btn.style.display = 'none';
        return;
    }

    btn.style.display = '';
    var applyState = function(pinned) {
        btn.textContent = pinned ? '取消置顶' : '置顶';
        if (pinned) btn.classList.add('is-pinned');
        else btn.classList.remove('is-pinned');
    };
    applyState(__isPinnedName(name));

    btn.onclick = function(ev) {
        if (ev && typeof ev.preventDefault === 'function') ev.preventDefault();
        if (ev && typeof ev.stopPropagation === 'function') ev.stopPropagation();
        if (btn.disabled) return;
        btn.disabled = true;
        __togglePin(dirRel, name)
            .then(function(data) {
                if (!data || !data.success || !data.data) {
                    showToast('置顶操作失败', 'error');
                    return;
                }
                var pins = Array.isArray(data.data.pins) ? data.data.pins : [];
                __rebuildPinMap(pins);
                __applyPinsToDom(getCurrentBrowsePath());
                applyState(!!data.data.pinned);
                showToast(data.data.pinned ? '已置顶' : '已取消置顶', 'success');
            })
            .catch(function() {
                showToast('置顶操作失败', 'error');
            })
            .finally(function() {
                btn.disabled = false;
            });
    };
}

function initPinsForCurrentDir() {
    var dir = getCurrentBrowsePath();
    __pinState.dir = dir;
    var pins = Array.isArray(window.__INITIAL_PINS__) ? window.__INITIAL_PINS__ : [];
    var pinDir = typeof window.__INITIAL_PIN_DIR__ === 'string' ? normalizeRelPath(window.__INITIAL_PIN_DIR__) : '';
    if (pinDir !== dir) pins = [];
    __rebuildPinMap(pins);
    __applyPinsToDom(dir);
}

function formatTimestampYYYYMMDDHHMMSS() {
    var d = new Date();
    var pad = function(n) { return String(n).padStart(2, '0'); };
    return String(d.getFullYear())
        + pad(d.getMonth() + 1)
        + pad(d.getDate())
        + pad(d.getHours())
        + pad(d.getMinutes())
        + pad(d.getSeconds());
}

function openArchiveProgressDrawer() {
    var fill = document.getElementById('archiveProgressFill');
    var text = document.getElementById('archiveProgressText');
    if (fill) fill.style.width = '0%';
    if (text) text.textContent = '准备中…';
    Drawer.open('archiveProgressDrawer');
}

function closeArchiveProgressDrawer() {
    if (window.__archiveProgressPoller && typeof window.__archiveProgressPoller.cancel === 'function') {
        window.__archiveProgressPoller.cancel();
    }
    window.__archiveProgressPoller = null;
    Drawer.close('archiveProgressDrawer');
}

function startArchiveProgressPoll(taskId) {
    if (!taskId || !window.TaskPoller || typeof window.TaskPoller.start !== 'function') return;
    openArchiveProgressDrawer();
    window.__archiveProgressPoller = window.TaskPoller.start(taskId, {
        intervalMs: 600,
        timeoutMs: 30 * 60 * 1000,
        onUpdate: function(evt) {
            var payload = evt && evt.payload ? evt.payload : null;
            var p = payload && typeof payload.progress === 'number' ? payload.progress : null;
            var msg = payload && typeof payload.message === 'string' ? payload.message : '';
            var fill = document.getElementById('archiveProgressFill');
            var text = document.getElementById('archiveProgressText');
            if (text && msg) text.textContent = msg;
            if (fill && p !== null && !Number.isNaN(p)) fill.style.width = String(Math.max(0, Math.min(100, p))) + '%';
        }
    });
    window.__archiveProgressPoller.promise.then(function(res) {
        if (res && res.ok) {
            showToast('压缩完成', 'success');
            closeArchiveProgressDrawer();
            if (typeof refreshFileList === 'function') doRefreshFileList();
            return;
        }
        var payload = res && res.payload ? res.payload : null;
        var msg = payload && (payload.message || (payload.error && payload.error.message)) ? (payload.message || (payload.error && payload.error.message)) : '';
        showToast(msg || '压缩失败', 'error');
        closeArchiveProgressDrawer();
    });
}

function openArchiveCreateDialog(paths, outputDir) {
    var items = Array.isArray(paths) ? paths.filter(function(p) { return typeof p === 'string' && p.trim(); }) : [];
    if (!items.length) {
        showToast('未选择可压缩项目', 'warning');
        return;
    }
    var outDir = typeof outputDir === 'string' ? normalizeRelPath(outputDir) : '';
    var defaultName = '新建压缩包.zip';

    if (typeof window.openDialogDrawer === 'function') {
        window.openDialogDrawer({
            title: '新建压缩包',
            message: '输入压缩包名称并选择格式（生成在同级目录）',
            input: true,
            placeholder: '例如：backup.zip',
            defaultValue: defaultName,
            confirmText: '开始压缩',
            select: {
                options: [
                    { value: 'zip', label: 'zip' },
                    { value: 'tar.gz', label: 'tar.gz' }
                ],
                defaultValue: 'zip'
            },
            onConfirm: function(result) {
                var name = result && typeof result.value === 'string' ? result.value.trim() : '';
                var fmt = result && typeof result.select === 'string' ? result.select.trim() : 'zip';
                if (!name) name = fmt === 'zip' ? '新建压缩包.zip' : '新建压缩包.tar.gz';
                if (fmt === 'zip' && !name.toLowerCase().endsWith('.zip')) name = name + '.zip';
                if (fmt === 'tar.gz' && !name.toLowerCase().endsWith('.tar.gz')) {
                    if (name.toLowerCase().endsWith('.tar')) name = name + '.gz';
                    else name = name + '.tar.gz';
                }
                fetch('/api/archive/create', {
                    method: 'POST',
                    headers: Object.assign({ 'Content-Type': 'application/json' }, (typeof authHeaders === 'function' ? authHeaders() : {})),
                    body: JSON.stringify({
                        paths: items,
                        output_dir: outDir,
                        name: name,
                        format: fmt
                    })
                })
                    .then(function(r) { return r.json(); })
                    .then(function(d) {
                        if (d && d.success && d.data && d.data.taskId) {
                            startArchiveProgressPoll(d.data.taskId);
                        } else {
                            showToast((d && d.error && d.error.message) || '创建任务失败', 'error');
                        }
                    })
                    .catch(function() { showToast('创建任务失败', 'error'); });
            }
        });
        return;
    }

    var picked = prompt('压缩包名称（默认：新建压缩包.zip）', defaultName);
    if (picked === null) return;
    fetch('/api/archive/create', {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, (typeof authHeaders === 'function' ? authHeaders() : {})),
        body: JSON.stringify({ paths: items, output_dir: outDir, name: picked, format: 'zip' })
    })
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d && d.success && d.data && d.data.taskId) startArchiveProgressPoll(d.data.taskId);
            else showToast((d && d.error && d.error.message) || '创建任务失败', 'error');
        })
        .catch(function() { showToast('创建任务失败', 'error'); });
}

function shareText(text) {
    var t = typeof text === 'string' ? text : '';
    if (!t) return;
    if (navigator.share && navigator.canShare && navigator.canShare({ text: t })) {
        // 优先使用原生分享（仅移动设备）
        navigator.share({ text: t }).catch(function() {});
        return;
    }
    // 不支持原生分享时，自动复制到剪贴板
    copyToClipboard(t);
    showToast('链接已复制到剪贴板', 'success');
}

function shareMenuDownloadUrl() {
    var path = window.currentItemPath || '';
    var url = window.location.origin + '/download/' + encodeURIComponent(path);
    shareText(url);
}

function shareMenuPath() {
    shareText(window.currentItemPath || '');
}

function batchArchive() {
    var paths = [];
    document.querySelectorAll('.file-checkbox:checked').forEach(function(c) {
        if (c && c.dataset && c.dataset.path) paths.push(c.dataset.path);
    });
    if (paths.length === 0) {
        showToast('请选择要压缩的文件', 'warning');
        return;
    }
    openArchiveCreateDialog(paths, getCurrentBrowsePath());
}

function showDragUploadOverlay(show) {
    var overlay = document.getElementById('dragUploadOverlay');
    if (!overlay) return;
    overlay.style.display = show ? 'flex' : 'none';
}

function openDragUploadDrawer(files) {
    var listEl = document.getElementById('dragUploadFileList');
    var targetEl = document.getElementById('dragUploadTargetPath');
    var fillEl = document.getElementById('dragUploadProgressFill');
    var textEl = document.getElementById('dragUploadProgressText');

    var arr = Array.from(files || []).filter(function(f) { return f && typeof f.name === 'string'; });
    if (!arr.length) return;

    var baseTs = formatTimestampYYYYMMDDHHMMSS();
    var renamed = arr.map(function(f, idx) {
        var name = f.name || '';
        var dot = name.lastIndexOf('.');
        var ext = dot >= 0 ? name.slice(dot) : '';
        if (arr.length === 1) return baseTs + ext;
        return baseTs + '_' + String(idx + 1) + ext;
    });

    window.__dragUploadState = { files: arr, renamed: renamed, uploading: false };

    if (targetEl) targetEl.value = getCurrentBrowsePath();
    if (fillEl) fillEl.style.width = '0%';
    if (textEl) textEl.textContent = '';
    if (listEl) {
        listEl.innerHTML = arr.map(function(f, i) {
            var size = typeof f.size === 'number' ? formatSize(f.size) : '';
            var type = f.type || 'application/octet-stream';
            return '<div style="display:flex;justify-content:space-between;gap:12px;padding:8px 6px;border-bottom:1px solid #f1f2f4;">'
                + '<div style="min-width:0;">'
                + '<div style="font-weight:600;word-break:break-all;">' + escapeHtml(f.name) + '</div>'
                + '<div style="font-size:12px;color:#6e7781;">' + escapeHtml(size) + (size ? ' · ' : '') + escapeHtml(type) + '</div>'
                + '</div>'
                + '<div style="font-family:monospace;font-size:12px;color:#57606a;white-space:nowrap;flex-shrink:0;">→ ' + escapeHtml(renamed[i]) + '</div>'
                + '</div>';
        }).join('');
    }
    Drawer.open('dragUploadDrawer');
}

function closeDragUploadDrawer() {
    window.__dragUploadState = null;
    showDragUploadOverlay(false);
    Drawer.close('dragUploadDrawer');
}

async function startDragUpload() {
    var state = window.__dragUploadState;
    if (!state || !Array.isArray(state.files) || !state.files.length) return;
    if (state.uploading) return;
    state.uploading = true;

    var targetEl = document.getElementById('dragUploadTargetPath');
    var targetDir = targetEl ? normalizeRelPath(targetEl.value || '') : '';
    var total = state.files.length;
    var fillEl = document.getElementById('dragUploadProgressFill');
    var textEl = document.getElementById('dragUploadProgressText');

    for (var i = 0; i < total; i++) {
        if (!window.__dragUploadState || !window.__dragUploadState.uploading) return;
        var f = state.files[i];
        var desired = state.renamed[i] || (formatTimestampYYYYMMDDHHMMSS() + (getFileExt(f.name || '') || ''));
        if (textEl) textEl.textContent = '上传中… ' + String(i + 1) + '/' + String(total);

        var fd = new FormData();
        fd.append('file', f, desired);
        fd.append('target_dir', targetDir);
        fd.append('filename', desired);

        try {
            var resp = await fetch('/api/upload', { method: 'POST', body: fd });
            var json = null;
            try { json = await resp.json(); } catch (e) { json = null; }
            if (!json || !json.success) {
                var msg = json && json.error && json.error.message ? json.error.message : '上传失败';
                showToast(msg, 'error');
                state.uploading = false;
                return;
            }
        } catch (e) {
            showToast('上传失败', 'error');
            state.uploading = false;
            return;
        }

        var pct = Math.round(((i + 1) * 1000) / total) / 10;
        if (fillEl) fillEl.style.width = String(pct) + '%';
    }

    state.uploading = false;
    showToast('上传完成', 'success');
    closeDragUploadDrawer();
    if (typeof refreshFileList === 'function') doRefreshFileList();
}

function openPasteImageDrawer(blob) {
    if (!blob) return;
    var targetEl = document.getElementById('pasteImageTargetPath');
    var nameEl = document.getElementById('pasteImageFilename');
    var imgEl = document.getElementById('pasteImagePreview');

    var type = String(blob.type || '').toLowerCase();
    var ext = '.png';
    if (type === 'image/jpeg' || type === 'image/jpg') ext = '.jpg';
    if (type === 'image/png') ext = '.png';

    var ts = formatTimestampYYYYMMDDHHMMSS();
    var filename = 'paste_' + ts + ext;

    if (targetEl) targetEl.value = getCurrentBrowsePath();
    if (nameEl) nameEl.value = filename;

    var url = URL.createObjectURL(blob);
    window.__pasteImageState = { blob: blob, url: url };
    if (imgEl) {
        imgEl.src = url;
        imgEl.style.display = 'block';
    }
    Drawer.open('pasteImageDrawer');
}

function closePasteImageDrawer() {
    var st = window.__pasteImageState;
    if (st && st.url) {
        try { URL.revokeObjectURL(st.url); } catch (e) {}
    }
    window.__pasteImageState = null;
    var imgEl = document.getElementById('pasteImagePreview');
    if (imgEl) {
        imgEl.src = '';
        imgEl.style.display = 'none';
    }
    Drawer.close('pasteImageDrawer');
}

async function savePasteImage() {
    var st = window.__pasteImageState;
    if (!st || !st.blob) return;
    var targetEl = document.getElementById('pasteImageTargetPath');
    var nameEl = document.getElementById('pasteImageFilename');
    var targetDir = targetEl ? normalizeRelPath(targetEl.value || '') : '';
    var filename = nameEl ? (nameEl.value || '').trim() : '';
    if (!filename) {
        showToast('请输入文件名', 'warning');
        return;
    }

    var file = null;
    try {
        file = new File([st.blob], filename, { type: st.blob.type || 'image/png' });
    } catch (e) {
        file = st.blob;
    }

    var fd = new FormData();
    fd.append('file', file, filename);
    fd.append('target_dir', targetDir);
    fd.append('filename', filename);

    try {
        var resp = await fetch('/api/upload', { method: 'POST', body: fd });
        var json = null;
        try { json = await resp.json(); } catch (e) { json = null; }
        if (!json || !json.success) {
            var msg = json && json.error && json.error.message ? json.error.message : '保存失败';
            showToast(msg, 'error');
            return;
        }
    } catch (e) {
        showToast('保存失败', 'error');
        return;
    }

    showToast('保存成功', 'success');
    closePasteImageDrawer();
    if (typeof refreshFileList === 'function') doRefreshFileList();
}

function initDragUploadAndPaste() {
    if (window.__dragUploadInited) return;
    window.__dragUploadInited = true;

    var dragCounter = 0;
    window.addEventListener('dragenter', function(e) {
        if (!e || !e.dataTransfer) return;
        if (e.dataTransfer.types && Array.from(e.dataTransfer.types).indexOf('Files') < 0) return;
        dragCounter += 1;
        showDragUploadOverlay(true);
    });
    window.addEventListener('dragleave', function(e) {
        dragCounter = Math.max(0, dragCounter - 1);
        if (dragCounter === 0) showDragUploadOverlay(false);
    });
    window.addEventListener('dragover', function(e) {
        if (!e || !e.dataTransfer) return;
        if (e.dataTransfer.types && Array.from(e.dataTransfer.types).indexOf('Files') < 0) return;
        e.preventDefault();
        showDragUploadOverlay(true);
    });
    window.addEventListener('drop', function(e) {
        if (!e || !e.dataTransfer) return;
        var files = e.dataTransfer.files;
        if (!files || files.length === 0) return;
        e.preventDefault();
        dragCounter = 0;
        showDragUploadOverlay(false);
        openDragUploadDrawer(files);
    });

    document.addEventListener('paste', function(e) {
        var ev = e || window.event;
        var cd = ev && ev.clipboardData ? ev.clipboardData : null;
        if (!cd || !cd.items) return;
        var imgItem = null;
        for (var i = 0; i < cd.items.length; i++) {
            var it = cd.items[i];
            if (it && it.kind === 'file' && String(it.type || '').toLowerCase().startsWith('image/')) {
                imgItem = it;
                break;
            }
        }
        if (!imgItem) return;
        var blob = imgItem.getAsFile ? imgItem.getAsFile() : null;
        if (!blob) return;
        if (ev.preventDefault) ev.preventDefault();
        openPasteImageDrawer(blob);
    });
}

function openEditor(path) {
    if (!path) return;
    window.location.href = '/edit/' + encodePathForUrl(path);
}

function isArchiveName(name) {
    var n = (name || '').toLowerCase();
    if (!n) return false;
    if (n.endsWith('.tar.gz')) return true;
    if (n.endsWith('.tar.bz2')) return true;
    if (n.endsWith('.tar.xz')) return true;
    var parts = n.split('.');
    if (parts.length < 2) return false;
    var ext = parts.pop();
    return ['zip', 'rar', 'tar', 'tgz', '7z'].indexOf(ext) >= 0;
}

function extractArchiveHere(path, name) {
    if (!path || !name) {
        return;
    }
    if (!isArchiveName(name)) {
        showToast('不是压缩包', 'error');
        return;
    }
    var normPath = (path || '').replace(/\\/g, '/');
    var lastSlash = normPath.lastIndexOf('/');
    var archiveDir = lastSlash >= 0 ? normPath.slice(0, lastSlash) : '';
    var filename = lastSlash >= 0 ? normPath.slice(lastSlash + 1) : normPath;
    var baseName = filename;
    if (filename.toLowerCase().endsWith('.zip')) {
        baseName = filename.slice(0, -4);
    }
    var defaultTarget = baseName;
    var rootEl = document.getElementById('rootDir');
    var rootVal = rootEl ? (rootEl.value || '') : '';
    var rootNorm = rootVal.replace(/\\/g, '/').replace(/\/+$/, '');
    var rootName = rootNorm ? rootNorm.split('/').pop() : '';
    var displayDir = (rootName ? ('/' + rootName) : '') + (archiveDir ? ('/' + archiveDir) : '');
    if (!displayDir) displayDir = '/';
    var msg = '输入解压目标目录（相对于当前文件夹）。相对于当前文件夹: ' + displayDir;

    var runExtract = function(targetDir) {
        var t = (targetDir || '').trim();
        if (!t) t = baseName;
        t = (t || '').replace(/\\/g, '/').replace(/^\/+/, '');
        if (archiveDir) t = archiveDir + '/' + t;
        var url = '/api/archive/extract/' + encodePathForUrl(path);
        fetch(url, {
            method: 'POST',
            headers: Object.assign({ 'Content-Type': 'application/json' }, (typeof authHeaders === 'function' ? authHeaders() : {})),
            body: JSON.stringify({ target_dir: t })
        })
            .then(function(r) {
                return r.json().catch(function() {
                    return { success: false, error: { message: '解压失败' } };
                });
            })
            .then(function(data) {
                if (data && data.success) {
                    showToast('解压完成', 'success');
                    if (typeof refreshFileList === 'function') doRefreshFileList();
                } else {
                    showToast((data && data.error && data.error.message) || (data && data.message) || '解压失败', 'error');
                }
            })
            .catch(function(err) {
                showToast('解压失败', 'error');
            });
    };

    if (typeof window.showPromptDrawer === 'function') {
        window.showPromptDrawer('解压到此处', msg, '例如：downloads/unpacked', defaultTarget, '解压', runExtract, true);
        return;
    }

    var target = prompt(msg, defaultTarget);
    if (target === null) return;
    runExtract(target);
}

function encodePathForUrl(path) {
    var p = (path || '').replace(/\\/g, '/');
    return encodeURIComponent(p).replace(/%2F/g, '/');
}

function getFileExt(name) {
    var n = (name || '').toLowerCase();
    if (!n) return '';
    if (n.endsWith('.tar.gz')) return '.tar.gz';
    if (n.endsWith('.tar.bz2')) return '.tar.bz2';
    if (n.endsWith('.tar.xz')) return '.tar.xz';
    if (n.startsWith('.') && n.indexOf('.', 1) === -1) return n;
    var idx = n.lastIndexOf('.');
    if (idx < 0) return '';
    return n.slice(idx);
}

function attachFileItemDefaultHandlers() {
    document.querySelectorAll('.file-item[data-path][data-name]').forEach(function(el) {
        if (el.dataset && el.dataset.defaultClickBound === 'true') return;
        if (el.dataset) el.dataset.defaultClickBound = 'true';
        el.addEventListener('click', function(ev) {
            var target = ev.target;
            if (target && (target.closest('.menu-btn') || target.closest('input[type="checkbox"]') || target.closest('a') || target.closest('button'))) {
                return;
            }
            var path = el.dataset.path || '';
            var name = el.dataset.name || '';
            var isDir = (el.dataset.isDir || '').toLowerCase() === 'true';
            if (!path && !name) return;

            if (isDir) {
                var nav = window.BrowseNavigator;
                if (nav && typeof nav.navigateTo === 'function') {
                    nav.navigateTo(path || '', { replace: false });
                } else {
                    var dirUrl = path ? ('/browse/' + encodePathForUrl(path)) : '/browse/';
                    window.location.assign(dirUrl);
                }
                return;
            }

            var ext = getFileExt(name);
            var chromeNativeExts = [
                '.pdf', '.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv',
                '.mp3', '.wav', '.flac', '.aac', '.m4a', '.ico', '.webp', '.avif',
                '.html', '.htm', '.txt', '.css', '.js', '.xml', '.svg'
            ];
            var imageExts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'];
            var archiveExts = ['.zip', '.rar', '.tar', '.tgz', '.7z', '.tar.gz', '.tar.bz2', '.tar.xz'];
            var mdExts = ['.md', '.markdown'];
            var officeExts = ['.xls', '.xlsx', '.doc', '.docx', '.ppt', '.pptx'];
            var excelExts = ['.xls', '.xlsx', '.xlsm', '.xlsb'];

            if (!ext) {
                downloadFile(path, { name: name, openInNewTab: true });
                return;
            }
            if (imageExts.indexOf(ext) >= 0) {
                if (typeof window.openPreview === 'function') window.openPreview(path, name);
                return;
            }
            if (archiveExts.indexOf(ext) >= 0) {
                if (typeof window.openPreview === 'function') window.openPreview(path, name);
                return;
            }
            if (excelExts.indexOf(ext) >= 0) {
                if (typeof window.openPreview === 'function') window.openPreview(path, name);
                return;
            }
            if (mdExts.indexOf(ext) >= 0) {
                window.open('/view/' + encodePathForUrl(path), '_blank', 'noopener');
                return;
            }
            if (ext === '.json') {
                window.open('/json/editor?path=' + encodeURIComponent(path), '_blank', 'noopener');
                return;
            }
            if (ext === '.yaml' || ext === '.yml' || ext === '.toml' || ext === '.ini' || ext === '.conf') {
                window.open('/yaml/editor?path=' + encodeURIComponent(path), '_blank', 'noopener');
                return;
            }
            // URL 文件：读取内容中的 URL 并新窗口打开
            if (ext === '.url') {
                fetch('/api/file/read?path=' + encodeURIComponent(path))
                    .then(function(r) { return r.json(); })
                    .then(function(d) {
                        if (d?.success && d?.data?.content) {
                            var match = d.data.content.match(/URL=(.+)/);
                            if (match && match[1]) {
                                window.open(match[1].trim(), '_blank');
                            }
                        }
                    })
                    .catch(function() {});
                return;
            }
            // 所有其他文件都用 /serve/ 让浏览器原生预览
            window.open('/serve/' + encodePathForUrl(path), '_blank', 'noopener');
        });
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        attachFileItemDefaultHandlers();
        initPinsForCurrentDir();
        initDragUploadAndPaste();
    });
} else {
    attachFileItemDefaultHandlers();
    initPinsForCurrentDir();
    initDragUploadAndPaste();
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

function closeLegacyConfirmModal() {
    Drawer.close('confirmModal');
}

function performDelete(path) {
    var p = typeof path === 'string' && path ? path : window.currentItemPath;
    fetch(`/delete/${encodeURIComponent(p)}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showToast('已移到回收站', 'success');
                doRefreshFileList();
            } else {
                showToast(data.message || '删除失败', 'error');
            }
        })
        .catch(() => showToast('删除失败', 'error'));
    if (document.getElementById('confirmModal') && document.getElementById('confirmModal').classList.contains('open')) {
        closeLegacyConfirmModal();
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
            doRefreshFileList();
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
            doRefreshFileList();
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
                doRefreshFileList();
            } else {
                showToast(data.message || '克隆失败', 'error');
            }
        })
        .catch(() => showToast('克隆失败', 'error'));
}

// 下载
function getDownloadDisplayName(path, preferredName) {
    if (preferredName) return preferredName;
    if (window.currentItemName) return window.currentItemName;
    var p = (path || '').replace(/\\/g, '/').replace(/\/+$/, '');
    if (!p) return '';
    return p.split('/').pop() || '';
}

function getFileSizeTextFromDom(path) {
    var p = String(path || '');
    var sizeText = '';
    document.querySelectorAll('.file-item[data-path]').forEach(function(el) {
        if (!el || !el.dataset) return;
        if (String(el.dataset.path || '') !== p) return;
        var sizeEl = el.querySelector('.file-size');
        if (!sizeEl) return;
        var t = String(sizeEl.textContent || '').trim();
        if (t && t !== '-') sizeText = t;
    });
    return sizeText;
}

function downloadFile(path, opts) {
    var p = typeof path === 'string' ? path : '';
    if (!p) return;
    var o = opts && typeof opts === 'object' ? opts : {};
    var name = getDownloadDisplayName(p, o.name || '');
    var openInNewTab = !!o.openInNewTab;
    var url = '/download/' + encodePathForUrl(p);

    var headers = (typeof window.authHeaders === 'function') ? window.authHeaders() : null;
    var fetchOpts = headers ? { headers: headers } : undefined;
    fetch('/api/file/info?path=' + encodeURIComponent(p), fetchOpts)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var info = data && data.success ? data.data : null;
            if (info && info.is_dir) {
                showToast('不能下载文件夹', 'warning');
                return;
            }

            var sizeText = '';
            if (info && typeof info.size_human === 'string' && info.size_human) sizeText = info.size_human;
            if (!sizeText && info && typeof info.size === 'number' && isFinite(info.size)) sizeText = formatSize(info.size);
            if (!sizeText) sizeText = getFileSizeTextFromDom(p);

            var lines = [];
            lines.push('确认下载？');
            if (name) lines.push('名称：' + name);
            if (sizeText) lines.push('大小：' + sizeText);
            if (info && (info.mtime || info.modified)) lines.push('修改：' + String(info.mtime || info.modified));
            lines.push('路径：' + p);

            var ok = window.confirm(lines.join('\n'));
            if (!ok) return;

            if (openInNewTab) window.open(url, '_blank', 'noopener');
            else window.location.href = url;
        })
        .catch(function() {
            var sizeText = getFileSizeTextFromDom(p);
            var lines = [];
            lines.push('确认下载？');
            if (name) lines.push('名称：' + name);
            if (sizeText) lines.push('大小：' + sizeText);
            lines.push('路径：' + p);
            var ok = window.confirm(lines.join('\n'));
            if (!ok) return;
            if (openInNewTab) window.open(url, '_blank', 'noopener');
            else window.location.href = url;
        });
}

function copyDownloadUrl(path) {
    const url = window.location.origin + '/download/' + encodeURIComponent(path);
    copyToClipboard(url);
}

function copyFilePath(path) {
    // 获取绝对路径
    var rootPath = document.getElementById('rootDir')?.value || '';
    var currentPath = document.getElementById('currentBrowsePath')?.value || '';
    
    if (!path) {
        copyToClipboard(path);
        return;
    }
    
    // 如果 path 已经是绝对路径，直接复制
    if (path.startsWith('/')) {
        copyToClipboard(path);
        return;
    }
    
    var absolutePath = path;
    
    // 如果有 rootPath，优先使用 rootPath
    if (rootPath) {
        // 检查当前路径相对于 rootPath 的部分
        if (currentPath && currentPath.startsWith(rootPath)) {
            var relativeFromRoot = currentPath.slice(rootPath.length);
            if (relativeFromRoot) {
                absolutePath = rootPath + relativeFromRoot + '/' + path;
            } else {
                absolutePath = rootPath + '/' + path;
            }
        } else {
            absolutePath = rootPath + '/' + path;
        }
    } else if (currentPath) {
        absolutePath = currentPath + '/' + path;
    }
    
    copyToClipboard(absolutePath);
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
    window.location.href = '/edit/' + encodePathForUrl(path);
}

// 添加到对话
function addToChat(path) {
    // 获取绝对路径
    var rootPath = document.getElementById('rootDir')?.value || '';
    var currentPath = document.getElementById('currentBrowsePath')?.value || '';
    
    if (!path) {
        var absolutePath = '';
    } else if (path.startsWith('/')) {
        var absolutePath = path;
    } else {
        var absolutePath = path;
        // 如果有 rootPath，优先使用 rootPath
        if (rootPath) {
            if (currentPath && currentPath.startsWith(rootPath)) {
                var relativeFromRoot = currentPath.slice(rootPath.length);
                if (relativeFromRoot) {
                    absolutePath = rootPath + relativeFromRoot + '/' + path;
                } else {
                    absolutePath = rootPath + '/' + path;
                }
            } else {
                absolutePath = rootPath + '/' + path;
            }
        } else if (currentPath) {
            absolutePath = currentPath + '/' + path;
        }
    }
    
    // 隐藏菜单
    if (typeof closeMenuModal === 'function') {
        closeMenuModal();
    }
    
    if (typeof window.openBotModal === 'function') {
        window.openBotModal();
    }
    
    const input = document.getElementById('botInput');
    if (input) {
        const prefix = absolutePath ? (absolutePath + '： ') : '';
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
                
                // 构建类型显示
                let typeHtml = info.is_dir ? '📁 文件夹' : '📄 文件';
                if (info.is_symlink) {
                    const isBroken = !info.target_exists;
                    typeHtml += ' → <span style="color:' + (isBroken ? '#ff4444' : '#58a6ff') + ';">软链接' + (isBroken ? ' (破损)' : '') + '</span>';
                }
                
                // 构建软链接目标行
                let linkRowHtml = '';
                if (info.is_symlink && info.link_target) {
                    linkRowHtml = `<tr style="border-bottom:1px solid #eee;"><td style="padding:10px;color:#666;">软链接目标</td><td style="padding:10px;font-family:monospace;word-break:break-all;color:#58a6ff;">${escapeHtml(info.link_target)}</td></tr>`;
                }
                
                content.innerHTML = `
                    <div style="padding: 16px 0;">
                        <div style="font-size: 18px; font-weight: bold; margin-bottom: 16px; word-break: break-all;">${escapeHtml(name)}</div>
                        <table style="width:100%;border-collapse:collapse;font-size:14px;">
                            <tr style="border-bottom:1px solid #eee;"><td style="padding:10px;color:#666;">路径</td><td style="padding:10px;font-family:monospace;word-break:break-all;">${escapeHtml(path)}</td></tr>
                            <tr style="border-bottom:1px solid #eee;"><td style="padding:10px;color:#666;">类型</td><td style="padding:10px;">${typeHtml}</td></tr>
                            ${linkRowHtml}
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

function doRefreshFileList() {
    // 调用全局的 refreshFileList（会尝试 Vue AJAX 刷新，回退到页面刷新）
    if (typeof window.refreshFileList === 'function') {
        window.refreshFileList();
    } else {
        window.location.reload();
    }
}

function formatSize(size) {
    if (size < 1024) { return size + ' B'; }
    if (size < 1024 * 1024) { return (size / 1024).toFixed(1) + ' KB'; }
    if (size < 1024 * 1024 * 1024) { return (size / 1024 / 1024).toFixed(1) + ' MB'; }
    return (size / 1024 / 1024 / 1024).toFixed(1) + ' GB';
}

function openSearchResultFolder(path, isDir) {
    var p = (path || '').toString().replace(/\\/g, '/').replace(/^\/+/, '').replace(/\/+$/, '');
    var dir = '';
    if (isDir) {
        var idx = p.lastIndexOf('/');
        dir = idx >= 0 ? p.slice(0, idx) : '';
    } else {
        var idx2 = p.lastIndexOf('/');
        dir = idx2 >= 0 ? p.slice(0, idx2) : '';
    }
    var enc = (typeof encodePathForUrl === 'function') ? encodePathForUrl(dir) : encodeURIComponent(dir).replace(/%2F/g, '/');
    window.location.href = dir ? ('/browse/' + enc) : '/browse/';
    return false;
}

function openSearchResultMenu(ev, el) {
    if (ev && typeof ev.stopPropagation === 'function') ev.stopPropagation();
    if (!el || !el.dataset) return false;
    var path = decodeURIComponent(el.dataset.path || '');
    var name = decodeURIComponent(el.dataset.name || '');
    var isDir = (el.dataset.isDir || '').toLowerCase() === 'true';
    if (typeof window.showMenuModal === 'function') {
        var rect = null;
        try {
            rect = el.getBoundingClientRect ? el.getBoundingClientRect() : null;
        } catch (e) {
            rect = null;
        }
        window.showMenuModal(path, name, isDir, { fromSearch: true, anchorRect: rect });
    }
    return false;
}

function doSearch() {
    var input = document.getElementById('searchInput');
    var keyword = input ? String(input.value || '').trim() : '';
    if (!keyword) return;
    var resultsContainer = document.getElementById('searchResults');
    if (resultsContainer) resultsContainer.innerHTML = '<div style="text-align:center;padding:20px;color:#666;">搜索中...</div>';
    fetch('/api/search?q=' + encodeURIComponent(keyword))
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var results = data && data.success && data.data ? data.data.results : null;
            if (!resultsContainer) return;
            if (results && results.length > 0) {
                resultsContainer.innerHTML = results.map(function(item) {
                    var rawPath = (item && item.path ? String(item.path) : '').replace(/\\/g, '/').replace(/^\/+/, '');
                    var rawName = item && item.name ? String(item.name) : '';
                    var isDir = !!(item && item.is_dir);
                    var icon = item && item.icon ? String(item.icon) : (isDir ? '📁' : '📄');
                    var safeName = (typeof escapeHtml === 'function') ? escapeHtml(rawName) : rawName;
                    var safePath = (typeof escapeHtml === 'function') ? escapeHtml(rawPath) : rawPath;
                    var encPath = encodeURIComponent(rawPath);
                    var encName = encodeURIComponent(rawName);
                    return (
                        '<div class="file-item search-result-item" data-path="' + safePath + '" data-name="' + safeName + '" data-is-dir="' + (isDir ? 'true' : 'false') + '">' +
                            '<div class="file-col-icon">' +
                                '<span class="file-icon">' + (typeof escapeHtml === 'function' ? escapeHtml(icon) : icon) + '</span>' +
                            '</div>' +
                            '<div class="file-col-info">' +
                                '<div class="file-name"><span>' + safeName + '</span></div>' +
                                '<div class="file-details-inline"><span>' + safePath + '</span></div>' +
                            '</div>' +
                            '<div class="file-col-actions" style="gap:8px;">' +
                                '<a href="#" class="preview-btn" title="所在文件夹" onclick="return openSearchResultFolder(decodeURIComponent(\'' + encPath + '\'), ' + (isDir ? 'true' : 'false') + ');">📁</a>' +
                                '<div class="menu-btn" data-path="' + encPath + '" data-name="' + encName + '" data-is-dir="' + (isDir ? 'true' : 'false') + '" onclick="return openSearchResultMenu(event, this);">' +
                                    '<span>⋮</span>' +
                                '</div>' +
                            '</div>' +
                        '</div>'
                    );
                }).join('');
                attachFileItemDefaultHandlers();
            } else {
                resultsContainer.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">未找到结果</div>';
            }
        })
        .catch(function() {
            if (resultsContainer) resultsContainer.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">搜索失败</div>';
        });
}

function openTrashDrawer(callbacks) {
    Drawer.open('trashDrawer', callbacks);
    loadTrashList();
}

function closeTrashDrawer(callbacks) {
    Drawer.close('trashDrawer', Object.assign({}, callbacks || {}, {
        afterClose: function() {
            var container = document.getElementById('trashListContainer');
            if (container) container.innerHTML = '';
            if (callbacks && typeof callbacks.afterClose === 'function') callbacks.afterClose();
        }
    }));
}

function loadTrashList() {
    var container = document.getElementById('trashListContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/trash/list', { headers: (typeof authHeaders === 'function') ? authHeaders() : {} })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var items = data && data.success && data.data ? data.data.items : null;
            if (!container) return;
            if (!items || items.length === 0) {
                container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">回收站是空的</div>';
                return;
            }
            container.innerHTML = items.map(function(item) {
                var rawName = item.name || '';
                var rawDisplayName = item.display_name || item.name || '';
                var displayName = (typeof escapeHtml === 'function') ? escapeHtml(rawDisplayName) : rawDisplayName;
                var deletedAt = (typeof escapeHtml === 'function') ? escapeHtml(item.deleted_at || '') : (item.deleted_at || '');
                var typeIcon = item.is_dir ? '📁' : '📄';
                return (
                    '<div style="padding:12px;border:1px solid #eee;border-radius:10px;margin-bottom:10px;background:#fff;display:flex;gap:12px;align-items:flex-start;">' +
                        '<div style="font-size:18px;line-height:1;">' + typeIcon + '</div>' +
                        '<div style="flex:1;min-width:0;">' +
                            '<div style="font-weight:600;word-break:break-word;white-space:pre-wrap;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">' +
                                '<span>' + displayName + '</span>' +
                                '<button class="modal-btn modal-btn-confirm" style="padding:4px 8px;border-radius:999px;font-size:12px;" data-trash-name="' + encodeURIComponent(rawName) + '" data-trash-default="' + encodeURIComponent(rawDisplayName) + '" onclick="restoreTrashItemFromButton(this)">还原</button>' +
                            '</div>' +
                            '<div style="margin-top:4px;color:#666;font-size:12px;">删除时间: ' + deletedAt + '</div>' +
                        '</div>' +
                    '</div>'
                );
            }).join('');
        })
        .catch(function() {
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败</div>';
        });
}

function restoreTrashItemFromButton(btn) {
    if (!btn || !btn.dataset) return;
    var rawName = decodeURIComponent(btn.dataset.trashName || '');
    var suggested = decodeURIComponent(btn.dataset.trashDefault || '');
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
                headers: Object.assign({ 'Content-Type': 'application/json' }, (typeof authHeaders === 'function') ? authHeaders() : {}),
                body: JSON.stringify({ target_path: targetPath })
            })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data && data.success) {
                        if (typeof showToast === 'function') showToast('还原成功', 'success');
                        loadTrashList();
                    } else {
                        if (typeof showToast === 'function') showToast((data && data.error && data.error.message) || '还原失败', 'error');
                    }
                })
                .catch(function() { if (typeof showToast === 'function') showToast('还原失败', 'error'); });
        }
    );
}

function clearTrash() {
    showConfirmDrawer(
        '清空回收站',
        '确定要清空回收站吗？此操作不可恢复。',
        '清空',
        function() {
            fetch('/api/trash/clear', { method: 'POST', headers: (typeof authHeaders === 'function') ? authHeaders() : {} })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data && data.success) {
                        if (typeof showToast === 'function') showToast('回收站已清空', 'success');
                        loadTrashList();
                    } else {
                        if (typeof showToast === 'function') showToast((data && data.error && data.error.message) || '清空失败', 'error');
                    }
                })
                .catch(function() { if (typeof showToast === 'function') showToast('清空失败', 'error'); });
        },
        true
    );
}

function openCreateMenuDrawer(callbacks) {
    Drawer.open('createMenuDrawer', callbacks);
}

function closeCreateMenuDrawer(callbacks) {
    Drawer.close('createMenuDrawer', callbacks);
}

function createMenuUpload() {
    closeCreateMenuDrawer();
    var input = document.getElementById('fileInputInline');
    if (input) input.click();
}

function createMenuNewFolder() {
    closeCreateMenuDrawer();
    showPromptDrawer(
        '新建文件夹',
        '请输入文件夹名称',
        '例如：assets',
        'new_folder',
        '创建',
        function(name) {
            var pickedName = (typeof name === 'string') ? name.trim() : '';
            if (!pickedName) {
                if (typeof showToast === 'function') showToast('名称不能为空', 'warning');
                return;
            }
            var currentPathEl = document.getElementById('currentBrowsePath');
            var currentPath = currentPathEl ? String(currentPathEl.value || '') : '';
            var url = currentPath ? '/mkdir/' + encodeURIComponent(currentPath) : '/mkdir';
            fetch(url, {
                method: 'POST',
                headers: Object.assign({ 'Content-Type': 'application/json' }, (typeof authHeaders === 'function') ? authHeaders() : {}),
                body: JSON.stringify({ name: pickedName })
            })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data && data.success) {
                        if (typeof showToast === 'function') showToast('创建成功', 'success');
                        doRefreshFileList();
                    } else {
                        if (typeof showToast === 'function') showToast((data && (data.message || (data.error && data.error.message))) || '创建失败', 'error');
                    }
                })
                .catch(function() { if (typeof showToast === 'function') showToast('创建失败', 'error'); });
        }
    );
}

function createMenuNewFile() {
    closeCreateMenuDrawer();
    showPromptDrawer(
        '新建文件',
        '请输入文件名',
        '例如：README.md',
        'new_file.txt',
        '创建',
        function(name) {
            var pickedName = (typeof name === 'string') ? name.trim() : '';
            if (!pickedName) {
                if (typeof showToast === 'function') showToast('名称不能为空', 'warning');
                return;
            }
            var currentPathEl = document.getElementById('currentBrowsePath');
            var currentPath = currentPathEl ? String(currentPathEl.value || '') : '';
            var url = currentPath ? '/touch/' + encodeURIComponent(currentPath) : '/touch';
            fetch(url, {
                method: 'POST',
                headers: Object.assign({ 'Content-Type': 'application/json' }, (typeof authHeaders === 'function') ? authHeaders() : {}),
                body: JSON.stringify({ name: pickedName })
            })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data && data.success) {
                        if (typeof showToast === 'function') showToast('创建成功', 'success');
                        doRefreshFileList();
                    } else {
                        if (typeof showToast === 'function') showToast((data && (data.message || (data.error && data.error.message))) || '创建失败', 'error');
                    }
                })
                .catch(function() { if (typeof showToast === 'function') showToast('创建失败', 'error'); });
        }
    );
}

// 网页快捷方式创建
function createMenuNewUrl() {
    closeCreateMenuDrawer();
    document.getElementById('urlShortcutName').value = '';
    document.getElementById('urlShortcutUrl').value = '';
    document.getElementById('urlShortcutDrawer').classList.add('open');
    document.getElementById('urlShortcutBackdrop').classList.add('open');
    setTimeout(function() { document.getElementById('urlShortcutName').focus(); }, 100);
}

function closeUrlShortcutDrawer() {
    document.getElementById('urlShortcutDrawer').classList.remove('open');
    document.getElementById('urlShortcutBackdrop').classList.remove('open');
}

function confirmUrlShortcut() {
    var name = document.getElementById('urlShortcutName').value.trim();
    var url = document.getElementById('urlShortcutUrl').value.trim();
    
    if (!name) {
        if (typeof showToast === 'function') showToast('请输入名称', 'warning');
        return;
    }
    if (!url) {
        if (typeof showToast === 'function') showToast('请输入网址', 'warning');
        return;
    }
    
    // 添加 .url 后缀
    var filename = name.endsWith('.url') ? name : name + '.url';
    var content = '[InternetShortcut]\nURL=' + url;
    
    var currentPathEl = document.getElementById('currentBrowsePath');
    var currentPath = currentPathEl ? String(currentPathEl.value || '') : '';
    var filePath = currentPath ? currentPath + '/' + filename : filename;
    
    fetch('/api/file/write', {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, (typeof authHeaders === 'function') ? authHeaders() : {}),
        body: JSON.stringify({ path: filePath, content: content })
    })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data && data.success) {
                if (typeof showToast === 'function') showToast('创建成功', 'success');
                doRefreshFileList();
                closeUrlShortcutDrawer();
            } else {
                if (typeof showToast === 'function') showToast((data && (data.message || (data.error && data.error.message))) || '创建失败', 'error');
            }
        })
        .catch(function() { if (typeof showToast === 'function') showToast('创建失败', 'error'); });
}

// 导出到 window
window.showMenuModal = showMenuModal;
window.openCurrentFolderMenu = openCurrentFolderMenu;
window.closeMenuModal = closeMenuModal;
window.closeMenuOnBackdrop = closeMenuOnBackdrop;
window.startDrag = startDrag;
window.handleMenuAction = handleMenuAction;
window.confirmDelete = confirmDelete;
window.closeLegacyConfirmModal = closeLegacyConfirmModal;
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
window.shareMenuDownloadUrl = shareMenuDownloadUrl;
window.shareMenuPath = shareMenuPath;
window.editFile = editFile;
window.openEditor = openEditor;
window.addToChat = addToChat;
// refreshFileList 在 globals.js 中定义，这里不覆盖
// window.refreshFileList = doRefreshFileList;
window.openArchiveCreateDialog = openArchiveCreateDialog;
window.closeArchiveProgressDrawer = closeArchiveProgressDrawer;
window.batchArchive = batchArchive;
window.closeDragUploadDrawer = closeDragUploadDrawer;
window.startDragUpload = startDragUpload;
window.closePasteImageDrawer = closePasteImageDrawer;
window.savePasteImage = savePasteImage;
window.openSearchResultFolder = openSearchResultFolder;
window.openSearchResultMenu = openSearchResultMenu;
window.doSearch = doSearch;
window.openTrashDrawer = openTrashDrawer;
window.closeTrashDrawer = closeTrashDrawer;
window.loadTrashList = loadTrashList;
window.restoreTrashItemFromButton = restoreTrashItemFromButton;
window.clearTrash = clearTrash;
window.openCreateMenuDrawer = openCreateMenuDrawer;
window.closeCreateMenuDrawer = closeCreateMenuDrawer;
window.createMenuUpload = createMenuUpload;
window.createMenuNewFolder = createMenuNewFolder;
window.createMenuNewFile = createMenuNewFile;
window.createMenuNewUrl = createMenuNewUrl;
window.closeUrlShortcutDrawer = closeUrlShortcutDrawer;
window.confirmUrlShortcut = confirmUrlShortcut;

// ============ Git状态栏 ============

// 获取当前路径（从URL或面包屑）
function getCurrentPathFromUrl() {
    var pathMatch = window.location.pathname.match(/\/browse\/(.*)/);
    if (pathMatch && pathMatch[1]) {
        return decodeURIComponent(pathMatch[1]);
    }
    return '';
}

// 加载Git状态
function loadGitStatusBar() {
    var bar = document.getElementById('gitStatusBar');
    if (!bar) return;

    var status = window.__INITIAL_GIT_STATUS__ || null;
    if (status && status.is_repo) {
        showGitStatusBar(status);
        return;
    }
    bar.style.display = 'none';
}

function showGitStatusBar(status) {
    var bar = document.getElementById('gitStatusBar');
    if (!bar) return;
    
    // 分支名
    var branchEl = document.getElementById('gitStatusBranch');
    if (branchEl) {
        branchEl.textContent = status.branch || 'unknown';
    }
    
    // 状态指示器
    var indicatorEl = document.getElementById('gitStatusIndicator');
    if (indicatorEl) {
        indicatorEl.textContent = status.has_changes ? '✗' : '●';
        indicatorEl.className = 'git-status-indicator ' + (status.has_changes ? 'dirty' : 'clean');
    }
    
    // 统计信息
    var statsEl = document.getElementById('gitStatusStats');
    if (statsEl && status.has_changes) {
        var stats = [];
        if (status.untracked > 0) stats.push('<span class="git-stat git-stat-untracked">[+' + status.untracked + ']</span>');
        if (status.added > 0) stats.push('<span class="git-stat git-stat-added">[A:' + status.added + ']</span>');
        if (status.modified > 0) stats.push('<span class="git-stat git-stat-modified">[~' + status.modified + ']</span>');
        if (status.deleted > 0) stats.push('<span class="git-stat git-stat-deleted">[-' + status.deleted + ']</span>');
        statsEl.innerHTML = stats.join('');
    } else if (statsEl) {
        statsEl.innerHTML = '<span style="color:#2da44e;">Clean</span>';
    }
    
    // 显示状态栏
    bar.style.display = 'flex';
}

// 从状态栏打开Git管理抽屉
function openGitModalFromBar() {
    if (typeof window.openGitModal === 'function') {
        // 传递当前路径，找到对应的仓库
        var path = getCurrentPathFromUrl();
        var rootDirEl = document.getElementById('rootDir');
        var rootDir = rootDirEl ? rootDirEl.value : '';
        
        // 构建完整路径
        var fullPath = rootDir;
        if (path) {
            // 确保路径格式正确
            fullPath = (rootDir ? rootDir + '/' + path : path).replace(/\/+/g, '/');
        }
        
        // 调用Git管理，传入当前路径
        if (typeof window.loadGitList === 'function') {
            Drawer.open('gitModal');
            window.loadGitList(fullPath);
        }
    }
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(loadGitStatusBar, 100);
});

// 页面可见性变化时刷新（从其他标签页切回）
document.addEventListener('visibilitychange', function() {
    if (!document.hidden && document.getElementById('gitStatusBar')) {
        loadGitStatusBar();
    }
});
