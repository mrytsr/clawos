// ============ 预览功能模块 ============
/* global Drawer, escapeHtml */

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

function openPreview(path, name) {
    var titleEl = document.getElementById('previewTitle');
    if (titleEl) titleEl.textContent = name || '预览';
    var content = document.getElementById('previewContent');
    if (!content) return;

    var ext = getFileExt(name);
    var url = '/serve/' + encodePathForUrl(path);
    var imageExts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'];
    var archiveExts = ['.zip', '.rar', '.tar', '.tgz', '.7z', '.tar.gz', '.tar.bz2', '.tar.xz'];

    if (imageExts.indexOf(ext) >= 0) {
        content.innerHTML = `
            <div style="display:flex;gap:10px;align-items:center;justify-content:center;padding:12px 12px 0 12px;flex-wrap:wrap;">
                <button class="modal-btn modal-btn-cancel" style="padding:8px 12px;border-radius:8px;" onclick="window.__imagePreviewZoom(-0.2)">-</button>
                <button class="modal-btn modal-btn-cancel" style="padding:8px 12px;border-radius:8px;" onclick="window.__imagePreviewZoom(0.2)">+</button>
                <button class="modal-btn modal-btn-cancel" style="padding:8px 12px;border-radius:8px;" onclick="window.__imagePreviewRotate(-90)">⟲</button>
                <button class="modal-btn modal-btn-cancel" style="padding:8px 12px;border-radius:8px;" onclick="window.__imagePreviewRotate(90)">⟳</button>
                <button class="modal-btn modal-btn-cancel" style="padding:8px 12px;border-radius:8px;" onclick="window.__imagePreviewReset()">重置</button>
            </div>
            <div id="imagePreviewStage" style="height:70vh;display:flex;align-items:center;justify-content:center;overflow:hidden;padding:12px;">
                <img id="imagePreviewImg" src="${url}" style="max-width:100%;max-height:100%;transform-origin:center center;user-select:none;touch-action:none;">
            </div>
        `;
        window.__imagePreviewState = { scale: 1, rotation: 0 };
        window.__applyImageTransform = function() {
            var img = document.getElementById('imagePreviewImg');
            if (!img) return;
            var s = window.__imagePreviewState ? window.__imagePreviewState.scale : 1;
            var r = window.__imagePreviewState ? window.__imagePreviewState.rotation : 0;
            img.style.transform = 'scale(' + s + ') rotate(' + r + 'deg)';
        };
        window.__imagePreviewZoom = function(delta) {
            if (!window.__imagePreviewState) window.__imagePreviewState = { scale: 1, rotation: 0 };
            var next = (window.__imagePreviewState.scale || 1) + delta;
            next = Math.max(0.2, Math.min(6, next));
            window.__imagePreviewState.scale = next;
            window.__applyImageTransform();
        };
        window.__imagePreviewRotate = function(deltaDeg) {
            if (!window.__imagePreviewState) window.__imagePreviewState = { scale: 1, rotation: 0 };
            window.__imagePreviewState.rotation = (window.__imagePreviewState.rotation || 0) + deltaDeg;
            window.__applyImageTransform();
        };
        window.__imagePreviewReset = function() {
            window.__imagePreviewState = { scale: 1, rotation: 0 };
            window.__applyImageTransform();
        };
        var stage = document.getElementById('imagePreviewStage');
        if (stage) {
            stage.onwheel = function(e) {
                if (!e) return;
                e.preventDefault();
                var delta = e.deltaY > 0 ? -0.12 : 0.12;
                window.__imagePreviewZoom(delta);
            };
        }
        Drawer.open('previewModal');
        return;
    }

    if (archiveExts.indexOf(ext) >= 0) {
        content.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
        Drawer.open('previewModal');
        fetch('/api/archive/list/' + encodePathForUrl(path), { headers: (typeof authHeaders === 'function' ? authHeaders() : {}) })
            .then(r => r.json())
            .then(data => {
                if (!data || !data.success || !data.data) {
                    var msg = (data && data.error && data.error.message) || (data && data.message) || '加载失败';
                    content.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">' + escapeHtml(msg) + '</div>';
                    return;
                }
                var items = data.data.items || [];
                if (!items.length) {
                    content.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">空压缩包</div>';
                    return;
                }
                content.innerHTML = items.map(function(it) {
                    var icon = it.is_dir ? '📁' : '📄';
                    var p = escapeHtml(it.path || '');
                    var size = it.is_dir ? '' : ('<span style="color:#999;font-size:12px;margin-left:8px;">' + escapeHtml(it.size_human || '') + '</span>');
                    return '<div style="padding:10px 2px;border-bottom:1px solid #eee;display:flex;align-items:center;gap:10px;">' +
                        '<span style="width:24px;text-align:center;">' + icon + '</span>' +
                        '<span style="flex:1;min-width:0;word-break:break-all;">' + p + '</span>' +
                        size +
                    '</div>';
                }).join('');
            })
            .catch(() => {
                content.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败</div>';
            });
        return;
    }

    content.innerHTML = `<div style="padding:40px;text-align:center;color:#666;">该文件类型不在抽屉预览范围</div>`;
    Drawer.open('previewModal');
}

function closePreviewModal() {
    Drawer.close('previewModal');
}

function closePreviewOnBackdrop(event) {
    if (event.target.id === 'previewModal') {
        closePreviewModal();
    }
}

// 点击行号复制文件路径:行号
function copyLineRef(element) {
    const path = element.dataset.path;
    const line = element.dataset.line;
    const text = `${path}:${line}`;
    
    navigator.clipboard.writeText(text).then(() => {
        // 简单的视觉反馈
        const originalColor = element.style.color;
        element.style.color = '#0969da';
        element.style.background = '#ddf4ff';
        setTimeout(() => {
            element.style.color = originalColor;
            element.style.background = '';
        }, 200);
    }).catch(() => {
        // 复制失败也给出提示（静默失败，不影响体验）
    });
}

// 导出
window.openPreview = openPreview;
window.closePreviewModal = closePreviewModal;
window.closePreviewOnBackdrop = closePreviewOnBackdrop;
window.copyLineRef = copyLineRef;
