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

function showToast(message, type, title) {
    console.log('showToast called:', message, type);
    var t = type || 'info';
    var container = document.getElementById('toastContainer');
    if (!container) { console.log('toastContainer not found'); return; }

    var toast = document.createElement('div');
    toast.className = 'toast toast-' + t;

    var icons = {
        success: '<svg class="toast-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>',
        error: '<svg class="toast-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>',
        warning: '<svg class="toast-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>',
        info: '<svg class="toast-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>'
    };

    var titleHtml = title ? '<div class="toast-title">' + escapeHtml(title) + '</div>' : '';
    
    toast.innerHTML = (icons[t] || icons.info) +
        '<div class="toast-content">' + titleHtml +
        '<div class="toast-message">' + escapeHtml(message) + '</div></div>' +
        '<button class="toast-close" onclick="this.parentElement.remove()">' +
        '<svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M4.646 4.646a.5.5 0 01.708 0L8 7.293l2.646-2.647a.5.5 0 01.708.708L8.707 8l2.647 2.646a.5.5 0 01-.708.708L8 8.707l-2.646 2.647a.5.5 0 01-.708-.708L7.293 8 4.646 5.354a.5.5 0 010-.708z"/></svg>' +
        '</button>';

    container.appendChild(toast);

    setTimeout(function() {
        toast.classList.add('toast-out');
        setTimeout(function() { toast.remove(); }, 200);
    }, 2000);
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

(function() {
    if (window.__drawerHistoryInited) return;
    window.__drawerHistoryInited = true;

    window.__drawerHistoryState = {
        hasPlaceholder: false,
        ignoreNextPop: false
    };

    function anyDrawerOpen() {
        return !!document.querySelector('.drawer.open, .right-drawer.open');
    }

    (function() {
        var syncScheduled = false;
        var lastOpen = anyDrawerOpen();

        function sync() {
            syncScheduled = false;
            var nowOpen = anyDrawerOpen();
            if (nowOpen && !lastOpen) {
                window.__drawerHistoryPush();
            } else if (!nowOpen && lastOpen) {
                window.__drawerHistoryClear();
            }
            lastOpen = nowOpen;
        }

        function scheduleSync() {
            if (syncScheduled) return;
            syncScheduled = true;
            setTimeout(sync, 0);
        }

        if (typeof MutationObserver !== 'undefined') {
            try {
                var obs = new MutationObserver(scheduleSync);
                obs.observe(document.documentElement, { subtree: true, attributes: true, attributeFilter: ['class'] });
            } catch (e) {}
        }

        scheduleSync();
    })();

    window.__drawerHistoryPush = function() {
        var st = window.__drawerHistoryState;
        if (!st || st.hasPlaceholder) return;
        if (!window.history || typeof window.history.pushState !== 'function') return;
        try {
            window.history.pushState({ __drawer_placeholder: true }, '', document.location.href);
            st.hasPlaceholder = true;
            if (typeof window.showToast === 'function') window.showToast('已添加后退占位', 'info');
        } catch (e) {}
    };

    window.__drawerHistoryClear = function() {
        var st = window.__drawerHistoryState;
        if (!st || !st.hasPlaceholder) return;
        if (!window.history || typeof window.history.back !== 'function') return;
        st.ignoreNextPop = true;
        st.hasPlaceholder = false;
        if (typeof window.showToast === 'function') window.showToast('已清除后退占位', 'info');
        try {
            window.history.back();
        } catch (e) {}
    };

    window.addEventListener('popstate', function() {
        var st = window.__drawerHistoryState;
        if (!st) return;
        if (st.ignoreNextPop) {
            st.ignoreNextPop = false;
            return;
        }

        if (!anyDrawerOpen()) return;

        if (st.hasPlaceholder) st.hasPlaceholder = false;

        if (typeof closeTopmostDrawer === 'function') {
            closeTopmostDrawer();
        } else if (typeof Drawer !== 'undefined' && Drawer && typeof Drawer.closeAll === 'function') {
            Drawer.closeAll();
        }

        setTimeout(function() {
            if (anyDrawerOpen()) window.__drawerHistoryPush();
        }, 0);
    });
})();

const Drawer = {
    open: function(modalId, opts) {
        var m = document.getElementById(modalId);
        var b = document.getElementById(modalId.replace('Modal', 'Backdrop').replace('Drawer', 'Backdrop'));
        if (m) m.classList.add('open');
        if (b) b.classList.add('open');
        if (opts && typeof opts.onOpen === 'function') opts.onOpen();
        dispatchDrawerEvent(modalId, 'drawer:open');
        if (typeof window.__updateScrollLock === 'function') window.__updateScrollLock();
        if (typeof window.__drawerHistoryPush === 'function') window.__drawerHistoryPush();
    },
    close: function(modalId, opts) {
        var m = document.getElementById(modalId);
        var b = document.getElementById(modalId.replace('Modal', 'Backdrop').replace('Drawer', 'Backdrop'));
        if (m) m.classList.remove('open');
        if (b) b.classList.remove('open');
        if (opts && typeof opts.onClose === 'function') opts.onClose();
        dispatchDrawerEvent(modalId, 'drawer:close');
        setTimeout(function() {
            if (!document.querySelector('.drawer.open, .right-drawer.open')) {
                if (typeof window.__drawerHistoryClear === 'function') window.__drawerHistoryClear();
            }
        }, 0);
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
    SwalGitHub.fire({
        title: title || '输入',
        text: message || '',
        input: 'text',
        inputPlaceholder: placeholder || '',
        inputValue: defaultValue || '',
        showCancelButton: true,
        confirmButtonText: confirmText || '确定',
        cancelButtonText: '取消',
        preConfirm: function() {
            var value = document.querySelector('.swal2-input').value;
            if (onConfirm) onConfirm(value);
        }
    });
};

window.showConfirmDrawer = function(title, message, confirmText, onConfirm, danger) {
    SwalGitHub.fire({
        icon: danger ? 'warning' : 'question',
        title: title || '确认',
        text: message || '',
        showCancelButton: true,
        confirmButtonText: confirmText || '确认',
        cancelButtonText: '取消',
        preConfirm: function() {
            if (onConfirm) onConfirm();
        }
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
window.closeConfirmModal = function() {
    var b = document.getElementById('confirmBackdrop');
    if (b) b.style.display = 'none';
};
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
            { action: 'process', icon: '📊', text: '进程管理' },
            { action: 'gpu', icon: '🖥️', text: '显卡管理' },
            { action: 'ollama', icon: '🦙', text: 'Ollama' },
            { action: 'ai_eval', icon: '🧠', text: 'AI评测' },
            { action: 'openclaw', icon: '⚙️', text: 'OpenClaw' },
            { action: 'pkg', icon: '📦', text: '包管理' },
            { action: 'perf', icon: '📈', text: '性能监控' },
            { action: 'network', icon: '🌐', text: '网络管理' },
            { action: 'users', icon: '👥', text: '用户管理' },
            { action: 'docker', icon: '🐳', text: 'docker管理' },
            { action: 'systemd', icon: '🔧', text: 'systemd管理' },
            { action: 'clash', icon: '🌐', text: 'Clash代理' },
            { action: 'frp', icon: '🔗', text: 'FRP内网穿透' },
            { action: 'disk', icon: '💾', text: '磁盘管理' },
            { action: 'cron', icon: '⏰', text: 'Cron管理' },
            { action: 'fileopen', icon: '📂', text: '文件打开方式' },
            { action: 'email', icon: '📧', text: '邮件配置' },
            { action: 'warehouse', icon: '🏭', text: '仓库管理' }
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
    'ai_eval': { url: '/ai/evaluate', target: '_blank' },
    'git': { modal: 'gitModal', load: 'loadGitList', open: 'openGitModal' },
    'process': { modal: 'processModal', load: 'loadProcessList', open: 'openProcessModal' },
    'perf': { func: 'openPerfDrawer' },
    'network': { func: 'openNetworkDrawer' },
    'users': { func: 'openUsersDrawer' },
    'pkg': { func: 'openPkgDrawer' },
    'docker': { modal: 'dockerModal', load: 'loadDockerTabs', open: 'openDockerModal' },
    'systemd': { modal: 'systemdModal', load: 'loadSystemdList', open: 'openSystemdModal' },
    'clash': { modal: 'clashModal', load: 'loadClashConfigEnhanced', open: 'openClashModal' },
    'frp': { modal: 'frpModal', load: 'loadFrpConfig', open: 'openFrpModal' },
    'cron': { url: '/cron/manager', target: '_blank' },
    'db': { url: '/db/manager', target: '_blank' },
    'disk': { modal: 'diskModal', load: 'loadDiskList', open: 'openDiskModal' },
    'network': { modal: 'networkModal', load: 'loadNetworkList', open: 'openNetworkModal' },
    'gpu': { modal: 'gpuModal', load: 'loadGpuInfo', open: 'openGpuModal' },
    'ollama': { modal: 'ollamaModal', load: 'loadOllamaModels', open: 'openOllamaModal' },
    'openclaw': { modal: 'openclawModal', load: 'loadOpenclawConfig', open: 'openOpenclawModal' },
    'cockpit': { path: '/home/tjx/cockpit.url', type: 'url' }
};

// 主菜单处理函数（需要在 globals.js 中定义，因为菜单项 onclick 使用）
window.handleMainMenu = function(action) {
    /* eslint-disable no-undef */
    if (action === 'bot') {
        openBotModal();
    } else if (action === 'terminal') {
        var currentPath = document.getElementById('currentBrowsePath') ? document.getElementById('currentBrowsePath').value : '';
        openTerminal(currentPath, true);
    } else if (action === 'warehouse') {
        window.open('/warehouse/', '_blank');
    } else if (action === 'fileopen') {
        window.open('/file-open-config', '_blank');
    } else if (action === 'email') {
        window.open('/email-config', '_blank');
    } else if (action === 'fileopen2') {
        window.open('/file-open-config', '_blank');
    } else if (action === 'config') {
        openConfigModal();
    } else if (action === 'pkg') {
        window.openPkgDrawer();
    } else if (window.actionToModalMap && window.actionToModalMap[action]) {
        var config = window.actionToModalMap[action];
        if (config.func && window[config.func]) {
            window[config.func]();
        } else if (config.url) {
            // 新窗口打开 URL
            var target = config.target || '_blank';
            window.open(config.url, target);
        } else if (config.type === 'url') {
            // 读取 URL 文件并新窗口打开
            fetch('/api/file/read?path=' + encodeURIComponent(config.path))
                .then(function(r) { return r.json(); })
                .then(function(d) {
                    if (d?.success && d?.data?.content) {
                        var match = d.data.content.match(/URL=(.+)/);
                        if (match && match[1]) {
                            window.open(match[1].trim(), '_blank');
                        } else {
                            alert('无法读取 URL 文件内容');
                        }
                    } else {
                        alert('文件不存在或无法读取: ' + config.path);
                    }
                })
                .catch(function(e) { 
                    alert('打开 URL 失败: ' + config.path); 
                });
        } else if (config.open && window[config.open]) {
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
    window.currentItemPath = path;
    window.currentItemName = name;
    window.currentItemIsDir = isDir;
    var t = document.getElementById('menuTitle');
    if (t) { t.textContent = name; }
    Drawer.open('menuModal');
};

// GitHub 风格确认框
window.__confirmCallback = null;
window.__confirmCancelCallback = null;
window.__confirmDanger = false;

window.showConfirm = function(title, message, onConfirm, danger, onCancel) {
    SwalGitHub.fire({
        icon: danger ? 'warning' : 'question',
        title: title || '确认操作',
        text: message || '确定要执行此操作吗？',
        showCancelButton: true,
        confirmButtonText: danger ? '删除' : '确认',
        cancelButtonText: '取消',
        preConfirm: function() {
            if (onConfirm) onConfirm();
        }
    }).then(function(result) {
        if (result.dismiss === 'cancel' && onCancel) {
            onCancel();
        }
    });
};

window.performConfirm = function() {
    var close = function() {
        window.__confirmCallback = null;
        window.__confirmCancelCallback = null;
        window.__confirmDanger = false;
        window.closeConfirmModal();
    };

    if (typeof window.__confirmCallback !== 'function') {
        close();
        return;
    }

    try {
        var ret = window.__confirmCallback();
        if (ret && typeof ret.then === 'function') {
            ret.then(close).catch(close);
            return;
        }
    } catch (e) {
        close();
        return;
    }
    close();
};

window.cancelConfirm = function() {
    var close = function() {
        window.__confirmCallback = null;
        window.__confirmCancelCallback = null;
        window.__confirmDanger = false;
        window.closeConfirmModal();
    };

    if (typeof window.__confirmCancelCallback !== 'function') {
        close();
        return;
    }

    try {
        var ret = window.__confirmCancelCallback();
        if (ret && typeof ret.then === 'function') {
            ret.then(close).catch(close);
            return;
        }
    } catch (e) {
        close();
        return;
    }
    close();
};

window.confirmDelete = function(path, name) {
    window.showConfirm(
        '删除 "' + (name || '') + '"',
        '此操作无法撤销，确定要继续吗？',
        function() { window.performDelete(path); },
        true
    );
};

// GitHub 风格 Alert
window.showAlert = function(title, message, type) {
    var b = document.getElementById('alertBackdrop');
    var icon = document.getElementById('alertIcon');
    var titleEl = document.getElementById('alertTitle');
    var msgEl = document.getElementById('alertMessage');
    var box = document.getElementById('alertBox');
    
    if (titleEl) titleEl.textContent = title || '';
    if (msgEl) msgEl.textContent = message || '';
    
    var t = type || 'info';
    if (icon) icon.className = 'gh-dialog-icon ' + t;
    if (box) box.className = 'gh-alert ' + t;
    
    if (b) b.style.display = 'flex';
    
    // 3秒后自动关闭
    setTimeout(function() { window.closeAlertModal(); }, 3000);
};

window.closeAlertModal = function() {
    var b = document.getElementById('alertBackdrop');
    if (b) b.style.display = 'none';
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
                showToast('删除成功 ' + paths.length + ' 个项目', 'success'); 
                refreshFileList(); 
            } else { 
                showToast(d.error?.message || '删除失败', 'error'); 
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
        showToast('已复制到剪贴板', 'success');
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
        showToast('已剪切到剪贴板', 'success');
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
            showToast(action === 'move' ? '移动成功' : '复制成功', 'success');
            window.clearSelection();
            refreshFileList();
        } else {
            showToast(d.error?.message || (action === 'move' ? '移动失败' : '复制失败'), 'error');
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
window.refreshFileList = function() {
    // 防止重复刷新的标志
    if (window.__refresh_pending__) {
        console.log('[refreshFileList] already pending, skip');
        return;
    }
    window.__refresh_pending__ = true;
    
    // 尝试调用 Vue 组件的 refreshItems 方法
    if (window.__browseVueApp__) {
        console.log('[refreshFileList] calling Vue refreshItems');
        window.__browseVueApp__.refreshItems();
        setTimeout(function() { window.__refresh_pending__ = false; }, 500);
        return;
    }
    
    // Vue 未初始化，reload
    console.log('[refreshFileList] Vue not ready, reload page');
    window.location.reload();
};
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

// ========== 包管理 ==========
window.pkgCurrentTab = 'system';
window.pkgData = { system: [], pip: [], npm: [] };
window.pkgFilter = '';

window.openPkgDrawer = function() {
    Drawer.open('pkgDrawer');
    document.getElementById('pkgDrawerBackdrop').style.display = 'block';
    window.loadPkgCurrentTab();
};

window.closePkgDrawer = function() {
    Drawer.close('pkgDrawer');
    document.getElementById('pkgDrawerBackdrop').style.display = 'none';
};

window.switchPkgTab = function(tab) {
    window.pkgCurrentTab = tab;
    document.querySelectorAll('.pkg-tab').forEach(function(el) {
        el.classList.toggle('active', el.dataset.tab === tab);
    });
    document.querySelectorAll('.pkg-tab-panel').forEach(function(el) {
        el.classList.toggle('active', el.id === 'pkg' + tab.charAt(0).toUpperCase() + tab.slice(1));
    });
    window.loadPkgCurrentTab();
};

window.loadPkgCurrentTab = function() {
    switch(window.pkgCurrentTab) {
        case 'system': window.loadSystemPackages(); break;
        case 'pip': window.loadPipPackages(); break;
        case 'npm': window.loadNpmPackages(); break;
        case 'source': window.loadSources(); break;
    }
};

window.loadSystemPackages = function() {
    var el = document.getElementById('pkgSystemList');
    el.innerHTML = '<div style="text-align:center;padding:20px;color:#666;">加载中...</div>';
    fetch('/api/system-packages/list').then(function(r){return r.json();}).then(function(data){
        if (data.success && data.data && data.data.packages) {
            window.pkgData.system = data.data.packages;
            window.renderPkgList('pkgSystemList', window.pkgData.system);
        } else {
            el.innerHTML = '<div style="text-align:center;padding:20px;color:#cf222e;">加载失败</div>';
        }
    }).catch(function(e){
        el.innerHTML = '<div style="text-align:center;padding:20px;color:#cf222e;">' + e.message + '</div>';
    });
};

window.loadPipPackages = function() {
    var el = document.getElementById('pkgPipList');
    el.innerHTML = '<div style="text-align:center;padding:20px;color:#666;">加载中...</div>';
    fetch('/api/pip/list').then(function(r){return r.json();}).then(function(data){
        if (data.success && data.data && data.data.packages) {
            window.pkgData.pip = data.data.packages;
            window.renderPkgList('pkgPipList', window.pkgData.pip);
        } else {
            el.innerHTML = '<div style="text-align:center;padding:20px;color:#cf222e;">加载失败</div>';
        }
    }).catch(function(e){
        el.innerHTML = '<div style="text-align:center;padding:20px;color:#cf222e;">' + e.message + '</div>';
    });
};

window.loadNpmPackages = function() {
    var el = document.getElementById('pkgNpmList');
    el.innerHTML = '<div style="text-align:center;padding:20px;color:#666;">加载中...</div>';
    fetch('/api/npm/list').then(function(r){return r.json();}).then(function(data){
        if (data.success && data.data && data.data.packages) {
            window.pkgData.npm = data.data.packages;
            window.renderPkgList('pkgNpmList', window.pkgData.npm);
        } else {
            el.innerHTML = '<div style="text-align:center;padding:20px;color:#cf222e;">加载失败</div>';
        }
    }).catch(function(e){
        el.innerHTML = '<div style="text-align:center;padding:20px;color:#cf222e;">' + e.message + '</div>';
    });
};

window.renderPkgList = function(elId, list) {
    var el = document.getElementById(elId);
    var filter = window.pkgFilter.toLowerCase();
    var filtered = list.filter(function(pkg) {
        var name = pkg.name || pkg;
        return name.toLowerCase().indexOf(filter) >= 0;
    });
    if (filtered.length === 0) {
        el.innerHTML = '<div style="text-align:center;padding:20px;color:#666;">无匹配项</div>';
        return;
    }
    var html = '';
    filtered.slice(0, 100).forEach(function(pkg) {
        var name = pkg.name || pkg;
        var version = pkg.version || '';
        html += '<div class="pkg-item" onclick="showPkgActions(\'' + name.replace(/'/g, "\\'") + '\')">' +
            '<span class="pkg-item-name">' + name + '</span>' +
            (version ? '<span class="pkg-item-version">' + version + '</span>' : '') +
            '</div>';
    });
    el.innerHTML = html;
};

window.showPkgActions = function(name) {
    window.showAlert('提示', '功能开发中...', 'info');
};

window.filterPkgList = function() {
    window.pkgFilter = document.getElementById('pkgSearchInput').value || '';
    switch(window.pkgCurrentTab) {
        case 'system': window.renderPkgList('pkgSystemList', window.pkgData.system); break;
        case 'pip': window.renderPkgList('pkgPipList', window.pkgData.pip); break;
        case 'npm': window.renderPkgList('pkgNpmList', window.pkgData.npm); break;
    }
};

// 源管理
window.loadSources = function() {
    // pip 源
    var pipSources = [
        { name: '官方源 (pypi.org)', url: 'https://pypi.org/simple' },
        { name: '阿里云', url: 'https://mirrors.aliyun.com/pypi/simple' },
        { name: '清华源', url: 'https://pypi.tuna.tsinghua.edu.cn/simple' },
        { name: '腾讯云', url: 'https://mirrors.cloud.tencent.com/pypi/simple' }
    ];
    var currentPip = localStorage.getItem('pip_source') || pipSources[1].url;
    document.getElementById('pipSourceCurrent').innerHTML = '<span style="color:#1a7f37;">✓</span> ' + 
        (pipSources.find(function(s) { return s.url === currentPip; }) || pipSources[0]).name;
    var pipHtml = pipSources.map(function(s) {
        return '<div class="source-item' + (s.url === currentPip ? ' active' : '') + '" onclick="switchPipSource(\'' + s.url + '\')">' +
            '<span class="source-item-name">' + s.name + '</span>' +
            '<span class="source-item-arrow">' + (s.url === currentPip ? '✓' : '→') + '</span></div>';
    }).join('');
    document.getElementById('pipSourceList').innerHTML = pipHtml;
    
    // npm 源
    var npmSources = [
        { name: '官方源 (registry.npmjs.org)', url: 'https://registry.npmjs.org' },
        { name: '淘宝/阿里', url: 'https://registry.npmmirror.com' }
    ];
    var currentNpm = localStorage.getItem('npm_source') || npmSources[1].url;
    document.getElementById('npmSourceCurrent').innerHTML = '<span style="color:#1a7f37;">✓</span> ' + 
        (npmSources.find(function(s) { return s.url === currentNpm; }) || npmSources[0]).name;
    var npmHtml = npmSources.map(function(s) {
        return '<div class="source-item' + (s.url === currentNpm ? ' active' : '') + '" onclick="switchNpmSource(\'' + s.url + '\')">' +
            '<span class="source-item-name">' + s.name + '</span>' +
            '<span class="source-item-arrow">' + (s.url === currentNpm ? '✓' : '→') + '</span></div>';
    }).join('');
    document.getElementById('npmSourceList').innerHTML = npmHtml;
};

window.switchPipSource = function(url) {
    localStorage.setItem('pip_source', url);
    window.loadSources();
    window.showAlert('提示', 'pip 源已切换为: ' + url, 'success');
};

window.switchNpmSource = function(url) {
    localStorage.setItem('npm_source', url);
    window.loadSources();
    window.showAlert('提示', 'npm 源已切换为: ' + url, 'success');
};

// ========== 批量操作 ==========

// ========== 性能监控 ==========
window.perfInterval = null;
window.perfLastNet = null;
window.perfLastTime = null;

window.openPerfDrawer = function() {
    Drawer.open('perfDrawer');
    document.getElementById('perfDrawerBackdrop').style.display = 'block';
    window.startPerfMonitor();
};

window.closePerfDrawer = function() {
    Drawer.close('perfDrawer');
    document.getElementById('perfDrawerBackdrop').style.display = 'none';
    window.stopPerfMonitor();
};

window.startPerfMonitor = function() {
    window.stopPerfMonitor();
    if (typeof echarts !== 'undefined') {
        initPerfChart();
    }
    updatePerfData();
    window.perfInterval = setInterval(updatePerfData, 2000);
};

window.stopPerfMonitor = function() {
    if (window.perfInterval) {
        clearInterval(window.perfInterval);
        window.perfInterval = null;
    }
};

// ECharts 实时图表
var perfChart = null;
var perfHistory = { cpu: [], mem: [], time: [] };
var MAX_HISTORY = 30;

function initPerfChart() {
    if (perfChart) return;
    var chartDom = document.getElementById('perfChart');
    if (!chartDom) return;
    
    perfChart = echarts.init(chartDom, 'dark');
    
    var option = {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        legend: { data: ['CPU', '内存'], top: 5, textStyle: { fontSize: 11 } },
        grid: { left: 40, right: 20, top: 30, bottom: 25 },
        xAxis: { 
            type: 'category', 
            boundaryGap: false,
            data: [],
            axisLabel: { fontSize: 10 }
        },
        yAxis: { 
            type: 'value', 
            min: 0, max: 100,
            axisLabel: { fontSize: 10, formatter: '{value}%' }
        },
        series: [
            {
                name: 'CPU',
                type: 'line',
                smooth: true,
                showSymbol: false,
                lineStyle: { width: 2, color: '#58a6ff' },
                areaStyle: { color: 'rgba(88,166,255,0.2)' },
                data: []
            },
            {
                name: '内存',
                type: 'line',
                smooth: true,
                showSymbol: false,
                lineStyle: { width: 2, color: '#2ea043' },
                areaStyle: { color: 'rgba(46,160,67,0.2)' },
                data: []
            }
        ]
    };
    
    perfChart.setOption(option);
    
    // 窗口大小变化时自适应
    window.addEventListener('resize', function() {
        if (perfChart) perfChart.resize();
    });
}

function updatePerfChart(cpuPct, memPct) {
    if (!perfChart) return;
    
    var now = new Date();
    var timeStr = now.getHours().toString().padStart(2,'0') + ':' + 
                  now.getMinutes().toString().padStart(2,'0') + ':' + 
                  now.getSeconds().toString().padStart(2,'0');
    
    perfHistory.time.push(timeStr);
    perfHistory.cpu.push(Math.round(cpuPct));
    perfHistory.mem.push(Math.round(memPct));
    
    // 保持历史数据长度
    if (perfHistory.time.length > MAX_HISTORY) {
        perfHistory.time.shift();
        perfHistory.cpu.shift();
        perfHistory.mem.shift();
    }
    
    perfChart.setOption({
        xAxis: { data: perfHistory.time },
        series: [
            { data: perfHistory.cpu },
            { data: perfHistory.mem }
        ]
    });
}

function updatePerfData() {
    fetch('/api/performance/realtime').then(function(r){return r.json();}).then(function(data){
        if (!data.success || !data.data) return;
        var d = data.data;
        
        // 更新时间
        var now = new Date();
        document.getElementById('perfUpdateTime').textContent = 
            now.getHours().toString().padStart(2,'0') + ':' + 
            now.getMinutes().toString().padStart(2,'0') + ':' + 
            now.getSeconds().toString().padStart(2,'0');
        
        // CPU
        var cpu = d.cpu || {};
        var cpuPct = cpu.percent || 0;
        document.getElementById('perfCpuFill').style.width = cpuPct + '%';
        document.getElementById('perfCpuText').textContent = Math.round(cpuPct) + '%';
        
        // 内存
        var mem = d.memory || {};
        var memPct = mem.percent || 0;
        document.getElementById('perfMemFill').style.width = memPct + '%';
        document.getElementById('perfMemText').textContent = 
            formatSize(mem.used || 0) + ' / ' + formatSize(mem.total || 0);
        
        // 更新 ECharts 图表
        if (typeof echarts !== 'undefined') {
            updatePerfChart(cpuPct, memPct);
        }
        
        // 磁盘
        var disk = d.disk || {};
        var diskPct = disk.percent || 0;
        document.getElementById('perfDiskFill').style.width = diskPct + '%';
        document.getElementById('perfDiskText').textContent = Math.round(diskPct) + '%';
        
        // 网络流量
        var net = d.network || {};
        var nowTime = Date.now();
        if (window.perfLastNet && window.perfLastTime) {
            var sent = (net.bytes_sent - window.perfLastNet.bytes_sent) / ((nowTime - window.perfLastTime) / 1000);
            var recv = (net.bytes_recv - window.perfLastNet.bytes_recv) / ((nowTime - window.perfLastTime) / 1000);
            document.getElementById('perfNetText').textContent = 
                '↓ ' + formatSize(recv) + '/s  ↑ ' + formatSize(sent) + '/s';
        }
        window.perfLastNet = net;
        window.perfLastTime = nowTime;
        
        // GPU
        var gpu = d.gpu || {};
        var gpuSection = document.getElementById('perfGpuSection');
        if (gpu.available) {
            gpuSection.style.display = 'block';
            var gpuPct = gpu.utilization || 0;
            document.getElementById('perfGpuFill').style.width = gpuPct + '%';
            document.getElementById('perfGpuText').textContent = Math.round(gpuPct) + '%';
            document.getElementById('perfGpuInfo').textContent = 
                formatSize((gpu.memory_used || 0) * 1024 * 1024) + ' / ' + 
                formatSize((gpu.memory_total || 0) * 1024 * 1024) + ' | ' + 
                (gpu.temperature || '--') + '°C';
        } else {
            gpuSection.style.display = 'none';
        }
    }).catch(function(){});
}

function formatSize(bytes) {
    if (!bytes) return '0 B';
    var sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    var i = Math.floor(Math.log(bytes) / Math.log(1024));
    return parseFloat((bytes / Math.pow(1024, i)).toFixed(1)) + ' ' + sizes[i];
}

// ========== 网络管理 ==========
window.openNetworkDrawer = function() {
    Drawer.open('networkDrawer');
    document.getElementById('networkDrawerBackdrop').style.display = 'block';
    loadNetworkData();
};

window.closeNetworkDrawer = function() {
    Drawer.close('networkDrawer');
    document.getElementById('networkDrawerBackdrop').style.display = 'none';
};

window.switchNetTab = function(tab) {
    document.querySelectorAll('.net-tab').forEach(function(el){
        el.classList.toggle('active', el.dataset.tab === tab);
    });
    document.getElementById('netInterfaces').style.display = tab === 'interfaces' ? 'block' : 'none';
    document.getElementById('netConnections').style.display = tab === 'connections' ? 'block' : 'none';
    loadNetworkData();
};

function loadNetworkData() {
    // 接口
    fetch('/api/network/interfaces').then(function(r){return r.json();}).then(function(data){
        if (!data.success || !data.data) return;
        var ifaces = data.data.interfaces || [];
        var html = '';
        ifaces.length === 0 ? html = '<div style="text-align:center;padding:20px;color:#666;">无网络接口</div>' :
        ifaces.forEach(function(i){
            html += '<div style="padding:12px;border-bottom:1px solid #eaecef;">' +
                '<div style="font-weight:500;margin-bottom:4px;">' + i.name + '</div>' +
                '<div style="font-size:12px;color:#57606a;">' +
                '<span style="margin-right:16px;">IP: ' + i.ip + '</span>' +
                '<span style="margin-right:16px;">↓ ' + formatSize(i.bytes_recv) + '</span>' +
                '<span>↑ ' + formatSize(i.bytes_sent) + '</span>' +
                '</div></div>';
        });
        document.getElementById('netInterfaces').innerHTML = html;
    }).catch(function(){});
    
    // 连接
    fetch('/api/network/connections').then(function(r){return r.json();}).then(function(data){
        if (!data.success || !data.data) return;
        var conns = data.data.connections || [];
        var html = '';
        if (conns.length === 0) {
            html = '<div style="text-align:center;padding:20px;color:#666;">无网络连接</div>';
        } else {
            conns.forEach(function(c){
                var color = c.status === 'ESTABLISHED' ? '#1a7f37' : '#57606a';
                html += '<div style="padding:8px 12px;border-bottom:1px solid #eaecef;font-size:12px;">' +
                    '<span style="color:#24292f;">' + c.local_addr + '</span>' +
                    ' → ' +
                    '<span style="color:' + color + ';">' + c.remote_addr + '</span>' +
                    '</div>';
            });
        }
        document.getElementById('netConnections').innerHTML = html;
    }).catch(function(){});
}

// ========== 用户管理 ==========
window.openUsersDrawer = function() {
    Drawer.open('usersDrawer');
    document.getElementById('usersDrawerBackdrop').style.display = 'block';
    loadUsersData();
};

window.closeUsersDrawer = function() {
    Drawer.close('usersDrawer');
    document.getElementById('usersDrawerBackdrop').style.display = 'none';
};

window.switchUserTab = function(tab) {
    document.querySelectorAll('.user-tab').forEach(function(el){
        el.classList.toggle('active', el.dataset.tab === tab);
    });
    document.getElementById('userUsers').style.display = tab === 'users' ? 'block' : 'none';
    document.getElementById('userGroups').style.display = tab === 'groups' ? 'block' : 'none';
    loadUsersData();
};

function loadUsersData() {
    // 用户
    fetch('/api/users/list').then(function(r){return r.json();}).then(function(data){
        if (!data.success || !data.data) return;
        var users = data.data.users || [];
        var html = '';
        if (users.length === 0) {
            html = '<div style="text-align:center;padding:20px;color:#666;">无用户</div>';
        } else {
            users.forEach(function(u){
                html += '<div style="padding:10px 12px;border-bottom:1px solid #eaecef;">' +
                    '<div style="font-weight:500;">' + u.name + '</div>' +
                    '<div style="font-size:11px;color:#57606a;margin-top:2px;">UID:' + u.uid + ' | Shell:' + u.shell + '</div>' +
                    '</div>';
            });
        }
        document.getElementById('userUsers').innerHTML = html;
    }).catch(function(){});
    
    // 组
    fetch('/api/users/groups').then(function(r){return r.json();}).then(function(data){
        if (!data.success || !data.data) return;
        var groups = data.data.groups || [];
        var html = '';
        if (groups.length === 0) {
            html = '<div style="text-align:center;padding:20px;color:#666;">无用户组</div>';
        } else {
            groups.forEach(function(g){
                var members = g.members || [];
                html += '<div style="padding:10px 12px;border-bottom:1px solid #eaecef;">' +
                    '<div style="font-weight:500;">' + g.name + '</div>' +
                    '<div style="font-size:11px;color:#57606a;margin-top:2px;">GID:' + g.gid + ' | 成员: ' + (members.length ? members.join(', ') : '无') + '</div>' +
                    '</div>';
            });
        }
        document.getElementById('userGroups').innerHTML = html;
    }).catch(function(){});
}

// ========== 批量操作 ==========

// ============ SweetAlert2 GitHub 风格封装 ============
if (typeof Swal === 'undefined') { var Swal = window.Sweetalert2; }
if (typeof Swal !== 'undefined') {
const SwalGitHub = Swal.mixin({
    background: '#161b22',
    color: '#c9d1d9',
    confirmButtonColor: '#238636',
    cancelButtonColor: '#21262d',
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    showCancelButton: true,
    focusConfirm: false,
    buttonsStyling: true,
    customClass: {
        popup: 'swal-popup-github',
        confirmButton: 'swal-confirm-github',
        cancelButton: 'swal-cancel-github'
    }
});
}

// GitHub 风格样式
const style = document.createElement('style');
style.textContent = `
    .swal2-container { z-index: 10000 !important; }
    .swal-popup-github { border: 1px solid #30363d; border-radius: 6px; box-shadow: 0 16px 32px rgba(0,0,0,0.5); }
    .swal-confirm-github { background: #238636 !important; color: #fff !important; border: 1px solid rgba(240,246,252,0.1) !important; border-radius: 6px !important; }
    .swal-confirm-github:hover { background: #2ea043 !important; }
    .swal-cancel-github { background: #21262d !important; color: #c9d1d9 !important; border: 1px solid #30363d !important; border-radius: 6px !important; }
    .swal-cancel-github:hover { background: #30363d !important; }
`;
document.head.appendChild(style);

// Alert 封装
window.SwalAlert = function(title, message, type) {
    type = type || 'info';
    const icons = { success: 'success', error: 'error', warning: 'warning', info: 'info' };
    return SwalGitHub.fire({
        icon: icons[type] || 'info',
        title: title || '',
        text: message || '',
        showCancelButton: false,
        timer: type === 'success' ? 2000 : undefined
    });
};

// Confirm 封装
window.SwalConfirm = function(title, message, onConfirm, type) {
    type = type || 'warning';
    const icons = { success: 'success', error: 'error', warning: 'warning', info: 'info' };
    return SwalGitHub.fire({
        icon: icons[type] || 'warning',
        title: title || '确认',
        text: message || '',
        preConfirm: function() {
            if (onConfirm) onConfirm();
        }
    });
};

// Prompt 封装
window.SwalPrompt = function(title, message, defaultValue, onConfirm) {
    return SwalGitHub.fire({
        title: title || '输入',
        text: message || '',
        input: 'text',
        inputValue: defaultValue || '',
        showCancelButton: true,
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        preConfirm: function(value) {
            if (onConfirm) onConfirm(value);
        }
    });
};

;