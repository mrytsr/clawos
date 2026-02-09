function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function showUploadStatus(message) {
    var statusDiv = document.getElementById('uploadStatus');
    if (statusDiv) {
        statusDiv.textContent = message;
        statusDiv.style.display = 'block';
        setTimeout(function() {
            statusDiv.style.display = 'none';
        }, 3000);
    }
}

function showToast(message, type) {
    var t = type || 'info';
    var container = document.getElementById('toastContainer');
    if (!container) return;

    var toast = document.createElement('div');
    toast.className = 'toast toast-' + t;

    var icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };

    toast.innerHTML =
        '<span style="font-size: 18px;">' + (icons[t] || icons.info) + '</span>' +
        '<span class="toast-message">' + escapeHtml(message) + '</span>';

    container.appendChild(toast);

    setTimeout(function() {
        toast.classList.add('toast-out');
        setTimeout(function() { toast.remove(); }, 300);
    }, 3000);
}

window.showToast = showToast;
window.escapeHtml = escapeHtml;
window.showUploadStatus = showUploadStatus;

// ============ 统一抽屉控制器 ============
function dispatchDrawerEvent(modalId, eventName, detail) {
    var el = document.getElementById(modalId);
    if (!el || typeof el.dispatchEvent !== 'function') return;
    var ev = null;
    try {
        ev = new CustomEvent(eventName, { detail: detail });
    } catch (e) {
        try {
            ev = document.createEvent('CustomEvent');
            ev.initCustomEvent(eventName, false, false, detail);
        } catch (e2) {
            ev = null;
        }
    }
    if (ev) el.dispatchEvent(ev);
}

const Drawer = {
    open: function(modalId, opts) {
        var m = document.getElementById(modalId);
        var b = document.getElementById(modalId.replace('Modal', 'Backdrop').replace('Drawer', 'Backdrop'));
        if (m) m.classList.add('open');
        if (b) b.classList.add('open');
        if (opts && typeof opts.onOpen === 'function') opts.onOpen();
        dispatchDrawerEvent(modalId, 'drawer:open');
        if (typeof window.__updateScrollLock === 'function') window.__updateScrollLock();
    },
    close: function(modalId, opts) {
        var m = document.getElementById(modalId);
        var b = document.getElementById(modalId.replace('Modal', 'Backdrop').replace('Drawer', 'Backdrop'));
        if (m) m.classList.remove('open');
        if (b) b.classList.remove('open');
        if (opts && typeof opts.onClose === 'function') opts.onClose();
        dispatchDrawerEvent(modalId, 'drawer:close');
        var afterClose = opts && typeof opts.afterClose === 'function' ? opts.afterClose : null;
        if (afterClose) {
            setTimeout(function() {
                afterClose();
                dispatchDrawerEvent(modalId, 'drawer:after-close');
                if (typeof window.__updateScrollLock === 'function') window.__updateScrollLock();
            }, 300);
        } else {
            setTimeout(function() {
                dispatchDrawerEvent(modalId, 'drawer:after-close');
                if (typeof window.__updateScrollLock === 'function') window.__updateScrollLock();
            }, 300);
        }
    },
    closeAll: function(opts) {
        var openDrawers = Array.prototype.slice.call(document.querySelectorAll('.drawer.open, .right-drawer.open')).map(function(el) { return el.id; }).filter(Boolean);
        openDrawers.forEach(function(id) { Drawer.close(id, opts); });
        document.querySelectorAll('.drawer-backdrop.open, .right-drawer-backdrop.open').forEach(function(el) { el.classList.remove('open'); });
        if (typeof window.__updateScrollLock === 'function') window.__updateScrollLock();
    }
};

// 认证头辅助函数
function authHeaders() {
    return {};
}

(function() {
    if (window.__scrollLockInited) return;
    window.__scrollLockInited = true;

    var state = {
        locked: false,
        scrollY: 0,
        prev: null
    };

    function anyOverlayOpen() {
        if (document.querySelector('.drawer-backdrop.open, .right-drawer-backdrop.open')) return true;
        var dragOverlay = document.getElementById('dragUploadOverlay');
        if (dragOverlay && dragOverlay.style && dragOverlay.style.display && dragOverlay.style.display !== 'none') return true;
        return false;
    }

    function lockBodyScroll() {
        if (state.locked) return;
        var body = document.body;
        if (!body) return;
        state.locked = true;
        state.scrollY = window.scrollY || window.pageYOffset || 0;
        state.prev = {
            overflow: body.style.overflow,
            position: body.style.position,
            top: body.style.top,
            left: body.style.left,
            right: body.style.right,
            width: body.style.width
        };
        body.style.overflow = 'hidden';
        body.style.position = 'fixed';
        body.style.top = '-' + String(state.scrollY) + 'px';
        body.style.left = '0';
        body.style.right = '0';
        body.style.width = '100%';
    }

    function unlockBodyScroll() {
        if (!state.locked) return;
        var body = document.body;
        if (!body) return;
        var prev = state.prev || {};
        body.style.overflow = prev.overflow || '';
        body.style.position = prev.position || '';
        body.style.top = prev.top || '';
        body.style.left = prev.left || '';
        body.style.right = prev.right || '';
        body.style.width = prev.width || '';
        var y = state.scrollY || 0;
        state.locked = false;
        state.prev = null;
        state.scrollY = 0;
        window.scrollTo(0, y);
    }

    function updateScrollLock() {
        if (anyOverlayOpen()) lockBodyScroll();
        else unlockBodyScroll();
    }

    window.__updateScrollLock = updateScrollLock;

    if (window.MutationObserver) {
        var obs = new MutationObserver(function() { updateScrollLock(); });
        obs.observe(document.documentElement, { subtree: true, attributes: true, attributeFilter: ['class', 'style'] });
    }

    document.addEventListener('touchmove', function(e) {
        if (!state.locked) return;
        var t = e && e.target ? e.target : null;
        if (t && t.closest && (t.closest('.drawer.open') || t.closest('.right-drawer.open'))) return;
        if (e && typeof e.preventDefault === 'function') e.preventDefault();
    }, { passive: false, capture: true });

    updateScrollLock();
})();

// 页面加载时关闭所有抽屉
(function() {
    Drawer.closeAll();
})();

function closeTopmostDrawer() {
    var drawers = Array.prototype.slice.call(document.querySelectorAll('.drawer.open, .right-drawer.open'));
    if (!drawers.length) return false;

    var top = null;
    var topZ = -Infinity;
    drawers.forEach(function(el) {
        var z = 0;
        try {
            var zs = window.getComputedStyle ? window.getComputedStyle(el).zIndex : '';
            z = parseInt(zs, 10);
            if (Number.isNaN(z)) z = 0;
        } catch (e) {
            z = 0;
        }
        if (z >= topZ) {
            topZ = z;
            top = el;
        }
    });

    if (!top || !top.id) return false;

    if (top.id === 'dialogDrawer' && typeof window.closeDialogDrawer === 'function') {
        window.closeDialogDrawer();
        return true;
    }
    if (top.id === 'mainMenuDrawer' && typeof window.closeMainMenuModal === 'function') {
        window.closeMainMenuModal();
        return true;
    }
    Drawer.close(top.id);
    return true;
}

document.addEventListener('keydown', function(e) {
    if (!e || e.key !== 'Escape') return;
    var active = document.activeElement;
    var menu = document.getElementById('mainMenuDrawer');
    if (menu && menu.classList.contains('open') && active && menu.contains(active)) {
        if (typeof window.closeMainMenuModal === 'function') {
            e.preventDefault();
            window.closeMainMenuModal();
        }
        return;
    }
    closeTopmostDrawer();
});

document.addEventListener('keydown', function(e) {
    if (!e) return;
    var target = e.target;
    var inTextField = !!(target && typeof target.matches === 'function' && target.matches('input, textarea'));
    if ((e.ctrlKey && e.key === 'f') || (e.key === '/' && !inTextField)) {
        e.preventDefault();
        if (typeof window.openSearchModal === 'function') window.openSearchModal();
    }
});

window.showTaskListener = function(text) {
    var bar = document.getElementById('taskListenerBar');
    var label = document.getElementById('taskListenerText');
    if (!bar) return;
    if (label) label.textContent = text || '正在监听任务状态…';
    bar.style.display = 'flex';
    bar.setAttribute('aria-hidden', 'false');
};

window.hideTaskListener = function() {
    var bar = document.getElementById('taskListenerBar');
    if (!bar) return;
    bar.style.display = 'none';
    bar.setAttribute('aria-hidden', 'true');
};

window.openDialogDrawer = function(opts) {
    var o = opts || {};
    window.__dialogDrawerState = {
        onConfirm: typeof o.onConfirm === 'function' ? o.onConfirm : null,
        hasSelect: !!o.select
    };

    var titleEl = document.getElementById('dialogTitle');
    var msgEl = document.getElementById('dialogMessage');
    var selectEl = document.getElementById('dialogSelect');
    var inputEl = document.getElementById('dialogInput');
    var btnEl = document.getElementById('dialogConfirmBtn');

    if (titleEl) titleEl.textContent = o.title || '提示';
    if (msgEl) msgEl.textContent = o.message || '';

    if (selectEl) {
        if (o.select && Array.isArray(o.select.options)) {
            selectEl.style.display = 'block';
            selectEl.innerHTML = '';
            o.select.options.forEach(function(opt) {
                if (!opt) return;
                var value = typeof opt === 'string' ? opt : opt.value;
                var label = typeof opt === 'string' ? opt : (opt.label || opt.value);
                if (typeof value !== 'string') return;
                var optionEl = document.createElement('option');
                optionEl.value = value;
                optionEl.textContent = label || value;
                selectEl.appendChild(optionEl);
            });
            if (typeof o.select.defaultValue === 'string') selectEl.value = o.select.defaultValue;
        } else {
            selectEl.style.display = 'none';
            selectEl.innerHTML = '';
        }
    }

    var needsInput = !!o.input;
    if (inputEl) {
        inputEl.style.display = needsInput ? 'block' : 'none';
        inputEl.value = o.defaultValue || '';
        inputEl.placeholder = o.placeholder || '';
        inputEl.onkeydown = function(ev) {
            if (ev && ev.key === 'Enter') confirmDialogDrawer();
        };
    }

    if (btnEl) {
        btnEl.textContent = o.confirmText || '确认';
        if (o.danger) {
            btnEl.style.background = '#dc3545';
        } else {
            btnEl.style.background = '#2da44e';
        }
    }

    Drawer.open('dialogDrawer', {
        onOpen: function() {
            if (needsInput && inputEl) inputEl.focus();
        }
    });
};

window.closeDialogDrawer = function() {
    Drawer.close('dialogDrawer', {
        afterClose: function() {
            var inputEl = document.getElementById('dialogInput');
            var selectEl = document.getElementById('dialogSelect');
            if (inputEl) {
                inputEl.value = '';
                inputEl.onkeydown = null;
            }
            if (selectEl) {
                selectEl.innerHTML = '';
                selectEl.style.display = 'none';
            }
            window.__dialogDrawerState = null;
        }
    });
};

window.confirmDialogDrawer = function() {
    var state = window.__dialogDrawerState;
    var inputEl = document.getElementById('dialogInput');
    var selectEl = document.getElementById('dialogSelect');
    var value = inputEl && inputEl.style.display !== 'none' ? (inputEl.value || '').trim() : null;
    var selected = selectEl && selectEl.style.display !== 'none' ? (selectEl.value || '').trim() : null;
    var handler = state && typeof state.onConfirm === 'function' ? state.onConfirm : null;
    closeDialogDrawer();
    if (handler) {
        if (state && state.hasSelect) {
            handler({ value: value, select: selected });
        } else {
            handler(value);
        }
    }
};

window.showPromptDrawer = function(title, message, placeholder, defaultValue, confirmText, onConfirm, danger) {
    openDialogDrawer({
        title: title,
        message: message,
        input: true,
        placeholder: placeholder,
        defaultValue: defaultValue,
        confirmText: confirmText,
        onConfirm: onConfirm,
        danger: !!danger
    });
};

window.showConfirmDrawer = function(title, message, confirmText, onConfirm, danger) {
    openDialogDrawer({
        title: title,
        message: message,
        input: false,
        confirmText: confirmText,
        onConfirm: onConfirm,
        danger: !!danger
    });
};

// ============ 全局函数预加载 ============
/* global XMLHttpRequest, XLSX, mammoth, setTimeout, setInterval, prompt, alert */

// 模态框关闭函数（统一使用遮罩层）
window.closeProcessModal = function() {
    var m = document.getElementById('processModal');
    var b = document.getElementById('processBackdrop');
    if (m) m.classList.remove('open');
    if (b) b.classList.remove('open');
};
window.closeSystemPackageModal = function() {
    var m = document.getElementById('systemPackageModal');
    var b = document.getElementById('systemPackageBackdrop');
    if (m) m.classList.remove('open');
    if (b) b.classList.remove('open');
};
window.closePipModal = function() {
    var m = document.getElementById('pipModal');
    var b = document.getElementById('pipBackdrop');
    if (m) m.classList.remove('open');
    if (b) b.classList.remove('open');
};
window.closeNpmModal = function() {
    var m = document.getElementById('npmModal');
    var b = document.getElementById('npmBackdrop');
    if (m) m.classList.remove('open');
    if (b) b.classList.remove('open');
};
window.closeDockerModal = function() {
    var m = document.getElementById('dockerModal');
    var b = document.getElementById('dockerBackdrop');
    if (m) m.classList.remove('open');
    if (b) b.classList.remove('open');
};
window.closeSystemdModal = function() {
    var m = document.getElementById('systemdModal');
    var b = document.getElementById('systemdBackdrop');
    if (m) m.classList.remove('open');
    if (b) b.classList.remove('open');
    if (window.__activeTaskPoller && typeof window.__activeTaskPoller.cancel === 'function') {
        window.__activeTaskPoller.cancel();
        window.__activeTaskPoller = null;
    }
    if (typeof window.hideTaskListener === 'function') window.hideTaskListener();
};
window.closeDiskModal = function() {
    var m = document.getElementById('diskModal');
    var b = document.getElementById('diskBackdrop');
    if (m) m.classList.remove('open');
    if (b) b.classList.remove('open');
};
window.closeNetworkModal = function() {
    var m = document.getElementById('networkModal');
    var b = document.getElementById('networkBackdrop');
    if (m) m.classList.remove('open');
    if (b) b.classList.remove('open');
};
window.closeGpuModal = function() {
    var m = document.getElementById('gpuModal');
    var b = document.getElementById('gpuBackdrop');
    if (m) m.classList.remove('open');
    if (b) b.classList.remove('open');
};
window.closeOllamaModal = function() {
    var m = document.getElementById('ollamaModal');
    var b = document.getElementById('ollamaBackdrop');
    if (m) m.classList.remove('open');
    if (b) b.classList.remove('open');
};
window.closeOpenclawModal = function() {
    var m = document.getElementById('openclawModal');
    var b = document.getElementById('openclawBackdrop');
    if (m) m.classList.remove('open');
    if (b) b.classList.remove('open');
};

// 通用关闭函数
window.closeMenuModal = function() { Drawer.close('menuModal'); };
window.closePreviewModal = function() { Drawer.close('previewModal'); };
window.closeConfirmModal = function() { Drawer.close('confirmModal'); };
window.closeRenameModal = function() { Drawer.close('renameModal'); };
window.closeMoveModal = function() { Drawer.close('moveModal'); };
window.closeSearchModal = function() { 
    Drawer.close('searchModal', {
        afterClose: function() {
            var results = document.getElementById('searchResults');
            var input = document.getElementById('searchInput');
            if (results) results.innerHTML = '';
            if (input) input.value = '';
        }
    });
};
window.closeDetailsModal = function() { 
    var m = document.getElementById('detailsModal'); 
    var b = document.getElementById('detailsBackdrop'); 
    if (m) { m.classList.remove('open'); m.classList.remove('bottom-sheet'); }
    if (b) b.classList.remove('open'); 
};
window.closeDetailsOnBackdrop = function(e) { if (e.target.id === 'detailsModal') { closeDetailsModal(); } };
window.closeConfigModal = function() { var m = document.getElementById('configModal'); var b = document.getElementById('configBackdrop'); if (m) m.classList.remove('open'); if (b) b.classList.remove('open'); };
window.closeBotModal = function() { 
    var d = document.getElementById('botDrawer'); 
    var b = document.getElementById('botBackdrop'); 
    if (d) d.classList.remove('open'); 
    if (b) b.classList.remove('open'); 
};
window.closeTerminal = function() { var d = document.getElementById('terminalDrawer'); var b = document.getElementById('terminalBackdrop'); if (d) { d.classList.remove('open'); } if (b) { b.classList.remove('open'); } };
window.__mainMenuState = window.__mainMenuState || { prevFocus: null, trapHandler: null };
window.closeMainMenuModal = function() {
    var d = document.getElementById('mainMenuDrawer');
    var b = document.getElementById('mainMenuBackdrop');
    var a = document.getElementById('srAnnouncer');
    if (d) {
        d.classList.remove('open');
        d.setAttribute('aria-hidden', 'true');
    }
    if (b) {
        b.classList.remove('open');
    }
    if (a) a.textContent = '开始菜单已关闭';
    if (window.__mainMenuState && window.__mainMenuState.trapHandler) {
        document.removeEventListener('keydown', window.__mainMenuState.trapHandler, true);
        window.__mainMenuState.trapHandler = null;
    }
    var prev = window.__mainMenuState ? window.__mainMenuState.prevFocus : null;
    if (prev && typeof prev.focus === 'function') {
        prev.focus();
    }
    if (window.__mainMenuState) window.__mainMenuState.prevFocus = null;
};

// 打开函数
window.openMainMenuModal = function() {
    var d = document.getElementById('mainMenuDrawer');
    var b = document.getElementById('mainMenuBackdrop');
    var a = document.getElementById('srAnnouncer');
    if (window.__mainMenuState) window.__mainMenuState.prevFocus = document.activeElement || null;
    if (d) {
        d.classList.add('open');
        d.setAttribute('aria-hidden', 'false');
    }
    if (b) {
        b.classList.add('open');
    }
    if (a) a.textContent = '开始菜单已打开';
    if (d && window.__mainMenuState && !window.__mainMenuState.trapHandler) {
        window.__mainMenuState.trapHandler = function(e) {
            if (!d.classList.contains('open')) return;
            if (e && e.key === 'Escape') {
                var active = document.activeElement;
                if (active && d.contains(active)) {
                    e.preventDefault();
                    closeMainMenuModal();
                }
                return;
            }
            if (!e || e.key !== 'Tab' || typeof d.querySelectorAll !== 'function') return;
            var focusable = Array.prototype.slice.call(d.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'));
            focusable = focusable.filter(function(el) {
                if (!el || el.disabled) return false;
                if (typeof el.offsetParent === 'undefined') return true;
                return el.offsetParent !== null;
            });
            if (focusable.length === 0) return;
            var first = focusable[0];
            var last = focusable[focusable.length - 1];
            var active = document.activeElement;
            if (active && !d.contains(active) && active !== d) return;
            if (e.shiftKey) {
                if (active === first || active === d) {
                    e.preventDefault();
                    last.focus();
                }
            } else {
                if (active === last) {
                    e.preventDefault();
                    first.focus();
                }
            }
        };
        document.addEventListener('keydown', window.__mainMenuState.trapHandler, true);
    }
    var closeBtn = document.getElementById('mainMenuCloseBtn');
    if (closeBtn && typeof closeBtn.focus === 'function') {
        closeBtn.focus();
    } else if (d && typeof d.focus === 'function') {
        d.focus();
    }
    var c = document.getElementById('mainMenuItems');
    if (c) {
        var items = [
            { action: 'bot', icon: '🤖', text: 'claw对话' },
            { action: 'terminal', icon: '🖥️', text: '终端' },
            { action: 'config', icon: '⚙️', text: '配置' },
            { action: 'process', icon: '📊', text: '进程管理' },
            { action: 'gpu', icon: '🖥️', text: '显卡' },
            { action: 'ollama', icon: '🦙', text: 'Ollama' },
            { action: 'openclaw', icon: '⚙️', text: 'OpenClaw' },
            { action: 'system-package', icon: '📦', text: '系统包管理' },
            { action: 'pip', icon: '🐍', text: 'pip包管理' },
            { action: 'npm', icon: '📦', text: 'npm包管理' },
            { action: 'docker', icon: '🐳', text: 'docker管理' },
            { action: 'systemd', icon: '🔧', text: 'systemd管理' },
            { action: 'disk', icon: '💾', text: '磁盘管理' },
            { action: 'network', icon: '🌐', text: '网络管理' }
        ];
        c.innerHTML = items.map(function(item) {
            return '<div class="modal-item menu-item" data-action="' + item.action + '"><span style="margin-right:12px;">' + item.icon + '</span>' + item.text + '</div>';
        }).join('');
        c.querySelectorAll('.menu-item[data-action]').forEach(function(el) {
            el.addEventListener('click', function(e) {
                e.stopPropagation();
                window.handleMainMenu(el.dataset.action);
            });
        });
    }
};

window.openBotModal = function() { 
    var d = document.getElementById('botDrawer'); 
    var b = document.getElementById('botBackdrop'); 
    if (d) d.classList.add('open'); 
    if (b) b.classList.add('open'); 
    if (typeof loadBotHistory === 'function') { loadBotHistory(); } 
    var t = localStorage.getItem('pywebdeck_bot_token'); 
    if (t) { if (typeof botConnect === 'function' && !botIsConnected) { botConnect(); } } 
};
window.toggleBotSettings = function() { var s = document.getElementById('botSettings'); if (s) { s.style.display = s.style.display === 'none' ? 'block' : 'none'; } };
window.openSearchModal = function() { 
    Drawer.open('searchModal');
    var input = document.getElementById('searchInput');
    if (input) input.focus();
};
window.resetSearch = function() {
    var results = document.getElementById('searchResults');
    var input = document.getElementById('searchInput');
    if (results) results.innerHTML = '';
    if (input) { input.value = ''; input.focus(); }
};
window.openConfigModal = function() { var m = document.getElementById('configModal'); var b = document.getElementById('configBackdrop'); if (m) m.classList.add('open'); if (b) b.classList.add('open'); };
window.logoutAuth = function() { window.location.href = '/logout'; };

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

// 主菜单处理函数（需要在 globals.js 中定义，因为菜单项 onclick 使用）
window.handleMainMenu = function(action) {
    /* eslint-disable no-undef */
    if (action === 'bot') {
        openBotModal();
    } else if (action === 'terminal') {
        var currentPath = document.getElementById('currentBrowsePath') ? document.getElementById('currentBrowsePath').value : '';
        openTerminal(currentPath, true);
    } else if (action === 'config') {
        openConfigModal();
    } else if (window.actionToModalMap && window.actionToModalMap[action]) {
        var config = window.actionToModalMap[action];
        if (config.open && window[config.open]) {
            window[config.open]();
        } else {
            Drawer.open(config.modal);
        }
        if (config.load && window[config.load]) window[config.load]();
    }
    /* eslint-enable no-undef */
};

// 文件操作函数
window.showMenuModal = function(path, name, isDir) {
    currentItemPath = path;
    currentItemName = name;
    currentItemIsDir = isDir;
    var t = document.getElementById('menuTitle');
    if (t) { t.textContent = name; }
    Drawer.open('menuModal');
};
window.confirmDelete = function(path, name) {
    if (window.showConfirmDrawer && typeof window.performDelete === 'function') {
        window.showConfirmDrawer(
            '删除',
            '确定要删除 "' + (name || '') + '" 吗？',
            '删除',
            function() { window.performDelete(path); },
            true
        );
        return;
    }
    document.getElementById('itemNameToDelete').textContent = name;
    Drawer.open('confirmModal');
};
window.showRenameModal = function() {
    Drawer.open('renameModal');
    document.getElementById('renameInput').value = currentItemName;
    setTimeout(function() { document.getElementById('renameInput').focus(); }, 100);
};
window.showMoveModal = function() {
    Drawer.open('moveModal');
    document.getElementById('targetPathInput').value = '';
};

// 全局状态
window.batchOperationFiles = [];
window.batchActionType = null; // 'copy' or 'move'

// 批量操作
window.clearSelection = function() { 
    document.querySelectorAll('.file-checkbox').forEach(function(c) { c.checked = false; }); 
    window.batchOperationFiles = [];
    Drawer.close('batchDrawer');
    updateBatchBar();
};

window.batchDelete = function() { 
    var paths = []; 
    document.querySelectorAll('.file-checkbox:checked').forEach(function(c) { paths.push(c.dataset.path); }); 
    if (paths.length === 0) { return showToast('请选择要删除的文件', 'warning'); } 

    var batchDrawer = document.getElementById('batchDrawer');
    if (batchDrawer && batchDrawer.classList.contains('open')) {
        Drawer.close('batchDrawer');
        window.__restoreBatchDrawerAfterDialog = true;
        var dialogEl = document.getElementById('dialogDrawer');
        if (dialogEl) {
            var restoreHandler = function() {
                dialogEl.removeEventListener('drawer:after-close', restoreHandler);
                if (window.__restoreBatchDrawerAfterDialog) {
                    window.__restoreBatchDrawerAfterDialog = false;
                    updateBatchBar();
                }
            };
            dialogEl.addEventListener('drawer:after-close', restoreHandler);
        }
    }
    
    window.showConfirmDrawer('批量删除', '确定要删除这 ' + paths.length + ' 个项目吗？', '删除', function() {
        fetch('/api/batch/delete', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({paths: paths}) 
        }).then(function(r) { return r.json(); })
        .then(function(d) { 
            if (d && d.success) { 
                showToast((d.data && d.data.message) || '删除成功', 'success'); 
                refreshFileList(); 
            } else { 
                showToast((d && d.error && d.error.message) || '删除失败', 'error'); 
            } 
        }).catch(function() { showToast('删除失败', 'error'); });
        window.clearSelection();
    }, true);
};

window.batchCopy = function() {
    var paths = [];
    document.querySelectorAll('.file-checkbox:checked').forEach(function(c) { paths.push(c.dataset.path); });
    if (paths.length === 0) { return showToast('请选择要复制的文件', 'warning'); }

    if (window.Clipboard && typeof window.Clipboard.set === 'function') {
        window.Clipboard.set('copy', paths);
        showToast('已复制 ' + paths.length + ' 个项目', 'success');
        window.clearSelection();
    } else {
        showToast('复制不可用', 'error');
    }
};

window.batchMove = function() {
    var paths = [];
    document.querySelectorAll('.file-checkbox:checked').forEach(function(c) { paths.push(c.dataset.path); });
    if (paths.length === 0) { return showToast('请选择要移动的文件', 'warning'); }

    if (window.Clipboard && typeof window.Clipboard.set === 'function') {
        window.Clipboard.set('cut', paths);
        showToast('已剪切 ' + paths.length + ' 个项目', 'success');
        window.clearSelection();
    } else {
        showToast('剪切不可用', 'error');
    }
};

// Target Modal Functions
window.openTargetModal = function(title) {
    var t = document.getElementById('targetModalTitle');
    if (t) t.textContent = title || '选择目标位置';
    document.getElementById('targetPathInput').value = '';
    Drawer.open('targetModal');
    setTimeout(function() { document.getElementById('targetPathInput').focus(); }, 100);
};

window.closeTargetModal = function() {
    Drawer.close('targetModal');
};

window.confirmTargetPath = function() {
    var target = document.getElementById('targetPathInput').value.trim();
    if (!target) { return showToast('请输入目标路径', 'warning'); }
    
    var paths = window.batchOperationFiles;
    var action = window.batchActionType;
    
    if (!paths || paths.length === 0) { return showToast('未选择文件', 'error'); }
    
    var endpoint = action === 'move' ? '/api/batch/move' : '/api/batch/copy';
    
    fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paths: paths, target: target })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
        if (d && d.success) {
            showToast((d.data && d.data.message) || (action === 'move' ? '移动成功' : '复制成功'), 'success');
            window.clearSelection();
            refreshFileList();
        } else {
            showToast((d && d.error && d.error.message) || (action === 'move' ? '移动失败' : '复制失败'), 'error');
        }
    })
    .catch(function() { showToast('操作失败', 'error'); });
    
    window.closeTargetModal();
};

// 拖拽
window.startDrag = function(e) {
    window.isDragging = true;
    window.startY = e.clientY || e.touches[0].clientY;
    var sheet = e.target.closest('.bottom-sheet');
    window.startHeight = sheet ? sheet.offsetHeight : 300;
    document.addEventListener('mousemove', onDrag);
    document.addEventListener('mouseup', endDrag);
    document.addEventListener('touchmove', onDrag);
    document.addEventListener('touchend', endDrag);
};

window.onDrag = function(e) {
    if (!window.isDragging) { return; }
    var currentY = e.clientY || e.touches[0].clientY;
    var delta = window.startY - currentY;
    var sheet = document.querySelector('.bottom-sheet[style*="display: block"]') || document.querySelector('.bottom-sheet');
    if (sheet) {
        var newHeight = Math.max(200, Math.min(window.innerHeight * 0.9, window.startHeight + delta));
        sheet.style.height = newHeight + 'px';
    }
};

window.endDrag = function() { window.isDragging = false; document.removeEventListener('mousemove', onDrag); document.removeEventListener('mouseup', endDrag); document.removeEventListener('touchmove', onDrag); document.removeEventListener('touchend', endDrag); };

// 其他
window.handleFileSelect = function(event) {
    var files = event.target.files;
    if (files.length > 0) {
        var formData = new FormData();
        for (var i = 0; i < files.length; i++) { formData.append('file', files[i]); }
        var currentPath = document.getElementById('currentBrowsePath') ? document.getElementById('currentBrowsePath').value : '';
        
        // 显示进度条
        var progressDiv = document.createElement('div');
        progressDiv.className = 'upload-progress';
        progressDiv.innerHTML = '<span>上传中...</span><div class="progress-bar"><div class="progress-fill" id="uploadProgressFill"></div></div>';
        document.body.appendChild(progressDiv);
        
        var xhr = new XMLHttpRequest();
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                var percent = Math.round((e.loaded / e.total) * 100);
                var fill = document.getElementById('uploadProgressFill');
                if (fill) { fill.style.width = percent + '%'; }
            }
        });
        
        xhr.addEventListener('load', function() {
            progressDiv.remove();
            if (xhr.status === 200) {
                showToast('上传成功', 'success');
                setTimeout(function() { window.location.reload(); }, 500);
            } else {
                showToast('上传失败', 'error');
            }
        });
        
        xhr.addEventListener('error', function() {
            progressDiv.remove();
            showToast('上传失败', 'error');
        });
        
        xhr.open('POST', '/upload/' + encodeURIComponent(currentPath));
        xhr.send(formData);
    }
    event.target.value = '';
};

window.updateFontSize = function(size) { document.documentElement.style.setProperty('--global-font-size', size + 'px'); localStorage.setItem('global_font_size', size); showToast('字体大小已更新', 'success'); };
window.handleSearchKeyup = function(e) { if (e.key === 'Enter' && typeof doSearch === 'function') { doSearch(); } };
window.refreshFileList = function() { window.location.reload(); };
window.toggleSelectAll = function(cb) { document.querySelectorAll('.file-checkbox').forEach(function(c) { c.checked = cb.checked; }); updateBatchBar(); };
window.toggleItemSelection = function(path, cb) { if (!cb.checked) { document.getElementById('batchSelectAll').checked = false; } updateBatchBar(); };

function updateBatchBar() {
    var count = document.querySelectorAll('.file-checkbox:checked').length;
    var countEl = document.getElementById('batchCount');
    if (countEl) { countEl.textContent = '已选 ' + count + ' 项'; }
    
    var d = document.getElementById('batchDrawer');
    if (count > 0) {
        if (d && !d.classList.contains('open')) {
            Drawer.open('batchDrawer');
        }
    } else {
        if (d && d.classList.contains('open')) {
            Drawer.close('batchDrawer');
        }
    }
}

// 全局变量（通过 window 对象暴露）
window.isDragging = false;
window.startY = 0;
window.startHeight = 0;
