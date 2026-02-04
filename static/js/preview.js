// ============ 预览功能模块 ============
/* global Drawer, escapeHtml */

// 打开文件预览
function openPreview(path, name) {
    const ext = name.split('.').pop().toLowerCase();
    const url = '/serve/' + encodeURIComponent(path);
    
    document.getElementById('previewTitle').textContent = name;
    const content = document.getElementById('previewContent');
    
    // 预览类型映射
    const imageTypes = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'];
    const pdfTypes = ['pdf'];
    const textTypes = ['txt', 'md', 'json', 'xml', 'js', 'css', 'html', 'htm', 'py', 'sh', 'yaml', 'yml', 'csv'];
    
    if (imageTypes.includes(ext)) {
        content.innerHTML = `<div style="text-align: center; padding: 20px;"><img src="${url}" style="max-width: 100%; max-height: 70vh;"></div>`;
    } else if (pdfTypes.includes(ext)) {
        content.innerHTML = `<div style="height: 100%;"><iframe src="${url}" style="width: 100%; height: 70vh; border: none;"></iframe></div>`;
    } else if (textTypes.includes(ext)) {
        // 获取文本内容显示
        fetch('/serve/' + encodeURIComponent(path))
            .then(r => r.text())
            .then(text => {
                const escapedText = escapeHtml(text);
                const isLong = text.length > 10000;
                const displayText = isLong ? escapedText.substring(0, 10000) + '\n\n... (内容过长，仅显示前10000字符)' : escapedText;
                
                // 生成带行号的 HTML
                const lines = displayText.split('\n');
                const linesWithNumbers = lines.map((line, i) => {
                    const lineNum = i + 1;
                    return `<span class="line-number" data-path="${escapeHtml(path)}" data-line="${lineNum}" onclick="copyLineRef(this)">${lineNum}</span>${line}`;
                }).join('\n');
                
                content.innerHTML = `<pre style="margin:0;padding:16px;background:#f6f8fa;white-space:pre-wrap;word-wrap:break-word;font-family:monospace;font-size:13px;line-height:1.5;">${linesWithNumbers}</pre>`;
            })
            .catch(() => {
                content.innerHTML = `<div style="padding:40px;color:#cf222e;text-align:center;">❌ 无法加载文件内容</div>`;
            });
    } else {
        content.innerHTML = `<div style="padding:40px;text-align:center;color:#666;">该文件类型无法预览</div>`;
    }
    
    document.getElementById('previewModal').style.display = 'block';
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
