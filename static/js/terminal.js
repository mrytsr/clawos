// ============ 终端功能模块 ============

let term = null;
let fitAddon = null;
let socket = null;
let termInitialized = false;
let isTermOpen = false;
let ctrlMode = false;
let altMode = false;
let _vvBound = false;
let _pendingOpenActions = null;
let _requestedCwd = '';
let _gestureBound = false;

function focusTerminal() {
    if (term && typeof term.focus === 'function') term.focus();
    const container = document.getElementById('terminal-container');
    if (!container || typeof container.querySelector !== 'function') return;
    const ta = container.querySelector('textarea');
    if (ta && typeof ta.focus === 'function') {
        try {
            ta.focus({ preventScroll: true });
        } catch (e) {
            ta.focus();
        }
    }
}

function sendToTerminal(input) {
    if (!input) return;
    if (socket && socket.connected) {
        socket.emit('input', { input: input });
    }
}

function bindTerminalGestures() {
    if (_gestureBound) return;
    const container = document.getElementById('terminal-container');
    if (!container) return;

    const minFont = 10;
    const maxFont = 24;
    const swipeMinPx = 70;
    const swipeMaxDyPx = 50;
    const swipeMinAbsDxOverDy = 1.6;

    let pinchStartDist = 0;
    let pinchStartFont = 0;
    let pinchActive = false;
    let rafId = 0;
    let pendingFont = 0;

    let swipeStartX = 0;
    let swipeStartY = 0;
    let swipeDx = 0;
    let swipeDy = 0;
    let swipeActive = false;
    let swipeTracking = false;

    function clampFont(n) {
        return Math.max(minFont, Math.min(maxFont, n));
    }

    function touchDist(t1, t2) {
        const dx = t1.clientX - t2.clientX;
        const dy = t1.clientY - t2.clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    function applyFontSize(size) {
        if (!term) return;
        const next = clampFont(Math.round(size));
        if (term.options && term.options.fontSize === next) return;
        term.options.fontSize = next;
        if (fitAddon) fitAddon.fit();
        if (socket && socket.connected && term) {
            socket.emit('resize', { cols: term.cols, rows: term.rows });
        }
    }

    function scheduleFont(size) {
        pendingFont = size;
        if (rafId) return;
        rafId = window.requestAnimationFrame(() => {
            rafId = 0;
            applyFontSize(pendingFont);
        });
    }

    container.addEventListener('touchstart', (e) => {
        if (!e || !e.touches) return;
        if (e.touches.length === 2) {
            pinchActive = true;
            swipeTracking = false;
            swipeActive = false;
            pinchStartDist = touchDist(e.touches[0], e.touches[1]);
            pinchStartFont = (term && term.options && typeof term.options.fontSize === 'number') ? term.options.fontSize : 14;
            try { e.preventDefault(); } catch (_) {}
            return;
        }
        if (e.touches.length === 1) {
            swipeTracking = true;
            swipeActive = false;
            swipeStartX = e.touches[0].clientX;
            swipeStartY = e.touches[0].clientY;
            swipeDx = 0;
            swipeDy = 0;
        }
    }, { passive: false });

    container.addEventListener('touchmove', (e) => {
        if (!e || !e.touches) return;
        if (pinchActive && e.touches.length === 2) {
            const d = touchDist(e.touches[0], e.touches[1]);
            if (pinchStartDist > 0) {
                const ratio = d / pinchStartDist;
                scheduleFont(pinchStartFont * ratio);
            }
            try { e.preventDefault(); } catch (_) {}
            return;
        }
        if (swipeTracking && e.touches.length === 1) {
            swipeDx = e.touches[0].clientX - swipeStartX;
            swipeDy = e.touches[0].clientY - swipeStartY;
            const adx = Math.abs(swipeDx);
            const ady = Math.abs(swipeDy);
            if (!swipeActive && adx > 12 && adx > ady) {
                swipeActive = true;
            }
            if (swipeActive) {
                try { e.preventDefault(); } catch (_) {}
            }
        }
    }, { passive: false });

    container.addEventListener('touchend', (e) => {
        if (!e) return;
        if (pinchActive) {
            if (!e.touches || e.touches.length < 2) {
                pinchActive = false;
                pinchStartDist = 0;
                pinchStartFont = 0;
            }
            return;
        }
        if (swipeTracking) {
            const adx = Math.abs(swipeDx);
            const ady = Math.abs(swipeDy);
            const absDxOverDy = ady ? (adx / ady) : 999;
            if (swipeActive && adx >= swipeMinPx && ady <= swipeMaxDyPx && absDxOverDy >= swipeMinAbsDxOverDy) {
                if (swipeDx < 0) {
                    sendToTerminal('\x02n');
                } else {
                    sendToTerminal('\x02p');
                }
                focusTerminal();
            }
            swipeTracking = false;
            swipeActive = false;
            swipeDx = 0;
            swipeDy = 0;
        }
    }, { passive: true });

    container.addEventListener('touchcancel', () => {
        pinchActive = false;
        swipeTracking = false;
        swipeActive = false;
        pinchStartDist = 0;
        pinchStartFont = 0;
        swipeDx = 0;
        swipeDy = 0;
    }, { passive: true });

    _gestureBound = true;
}

function normalizeRelPathForWorkspace(path) {
    return (path || '').toString().replace(/\\/g, '/').replace(/^\/+/, '').replace(/\/+$/, '');
}

function bashDoubleQuote(str) {
    const s = (str || '').toString();
    return '"' + s.replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
}

function quoteIfNeeded(str) {
    const s = (str || '').toString();
    if (!s) return '';
    if (/^[A-Za-z0-9_.\-]+$/.test(s)) return s;
    return bashDoubleQuote(s);
}

function tryRunPendingOpenActions() {
    if (!_pendingOpenActions) return;
    if (!socket || !socket.connected) return;

    const actions = _pendingOpenActions;
    _pendingOpenActions = null;

    if (actions.cdPath) {
        sendToTerminal('cd -- ' + bashDoubleQuote(actions.cdPath) + '\r');
    }

    if (actions.prefillText) {
        setTimeout(() => {
            sendToTerminal(actions.prefillText);
            focusTerminal();
        }, 120);
        return;
    }

    focusTerminal();
}

function setPendingOpenActions(actions) {
    _pendingOpenActions = actions || null;
    tryRunPendingOpenActions();
}

function syncModifierButtons() {
    const drawer = document.getElementById('terminalDrawer');
    if (!drawer || typeof drawer.querySelectorAll !== 'function') return;
    const btns = drawer.querySelectorAll('.terminal-keyboard [data-mod]');
    btns.forEach((b) => {
        const mod = b.getAttribute('data-mod');
        const active = (mod === 'ctrl' && ctrlMode) || (mod === 'alt' && altMode);
        if (active) b.classList.add('active');
        else b.classList.remove('active');
    });
}

function stopBtnEvent(e) {
    if (!e) return;
    if (typeof e.preventDefault === 'function') e.preventDefault();
    if (typeof e.stopPropagation === 'function') e.stopPropagation();
    const t = e.currentTarget;
    if (t && typeof t.blur === 'function') t.blur();
}

function keySeq(key) {
    if (key === 'tab') return '\t';
    if (key === 'esc') return '\x1b';
    if (key === 'enter') return '\r';
    if (key === 'up') return '\x1b[A';
    if (key === 'down') return '\x1b[B';
    if (key === 'left') return '\x1b[D';
    if (key === 'right') return '\x1b[C';
    if (key === 'home') return '\x1b[H';
    if (key === 'end') return '\x1b[F';
    if (key === 'pgup') return '\x1b[5~';
    if (key === 'pgdn') return '\x1b[6~';
    if (key === 'slash') return '/';
    if (key === 'dash') return '-';
    if (key === 'backspace') return '\x7f';
    return '';
}

function applyModifiersToData(data) {
    if (!data) return '';
    const first = data[0];
    const rest = data.length > 1 ? data.slice(1) : '';

    let out = data;
    if (ctrlMode) {
        const c = String(first).toLowerCase();
        const code = c.charCodeAt(0);
        if (code >= 97 && code <= 122) {
            out = String.fromCharCode(code - 96) + rest;
        } else {
            out = data;
        }
        ctrlMode = false;
        altMode = false;
        syncModifierButtons();
        return out;
    }

    if (altMode) {
        out = '\x1b' + data;
        ctrlMode = false;
        altMode = false;
        syncModifierButtons();
        return out;
    }

    return out;
}

function handleKeyBtn(e, key) {
    stopBtnEvent(e);
    if (key === 'ctrl') {
        ctrlMode = !ctrlMode;
        if (ctrlMode && altMode) altMode = false;
        syncModifierButtons();
        focusTerminal();
        return false;
    }
    if (key === 'alt') {
        altMode = !altMode;
        if (altMode && ctrlMode) ctrlMode = false;
        syncModifierButtons();
        focusTerminal();
        return false;
    }

    const seq = keySeq(key);
    if (seq) sendToTerminal(seq);
    focusTerminal();
    return false;
}

function updateTerminalDrawerLayout() {
    const drawer = document.getElementById('terminalDrawer');
    if (!drawer) return;

    const vv = window.visualViewport;
    if (vv) {
        const overlap = Math.max(0, Math.round(window.innerHeight - vv.height - vv.offsetTop));
        drawer.style.bottom = overlap ? (String(overlap) + 'px') : '';
        const desired = Math.max(240, Math.round(vv.height * 0.8));
        drawer.style.height = String(desired) + 'px';
        drawer.style.maxHeight = String(desired) + 'px';
    } else {
        drawer.style.bottom = '';
        drawer.style.height = '';
        drawer.style.maxHeight = '';
    }
}

function openTerminal(path, isDir) {
    closeMenuModal();
    isTermOpen = true;
    
    // 计算路径
    const rootEl = document.getElementById('rootDir');
    const workspaceRoot = ((rootEl && rootEl.value) ? rootEl.value : '/root/.openclaw/workspace')
        .toString()
        .replace(/\\/g, '/')
        .replace(/\/+$/, '');
    const rel = normalizeRelPathForWorkspace(path);
    let termPath = workspaceRoot;
    let cdPath = workspaceRoot;
    let prefillText = '';
    if (rel) {
        if (isDir) {
            termPath = workspaceRoot + '/' + rel;
            cdPath = termPath;
        } else {
            const lastSlash = rel.lastIndexOf('/');
            const dirRel = lastSlash >= 0 ? rel.substring(0, lastSlash) : '';
            const base = lastSlash >= 0 ? rel.substring(lastSlash + 1) : rel;
            termPath = dirRel ? (workspaceRoot + '/' + dirRel) : workspaceRoot;
            cdPath = termPath;
            prefillText = quoteIfNeeded(base);
        }
    }
    
    const pathEl = document.getElementById('termPath');
    if (pathEl) pathEl.textContent = termPath;
    _requestedCwd = termPath;
    
    const drawer = document.getElementById('terminalDrawer');
    const backdrop = document.getElementById('terminalBackdrop');
    
    if (drawer) drawer.classList.add('open');
    if (backdrop) backdrop.classList.add('open');
    
    if (!termInitialized) {
        initTerminal(termPath);
        termInitialized = true;
    } else if (socket && !socket.connected) {
        socket.connect();
    }

    if (rel) {
        setPendingOpenActions({ cdPath: cdPath, prefillText: prefillText });
    } else {
        setPendingOpenActions(null);
    }
    
    setTimeout(() => {
        if (fitAddon) {
            fitAddon.fit();
            if (socket && socket.connected && term) {
                socket.emit('resize', { cols: term.cols, rows: term.rows });
            }
        }
        updateTerminalDrawerLayout();
        if (!_vvBound && window.visualViewport) {
            _vvBound = true;
            window.visualViewport.addEventListener('resize', function() {
                if (!isTermOpen) return;
                updateTerminalDrawerLayout();
            });
            window.visualViewport.addEventListener('scroll', function() {
                if (!isTermOpen) return;
                updateTerminalDrawerLayout();
            });
        }
        focusTerminal();
    }, 300);
}

function initTerminal(cwd) {
    term = new Terminal({
        cursorBlink: true,
        fontSize: 14,
        fontFamily: 'Menlo, Monaco, "Courier New", monospace',
        theme: { background: '#000000' }
    });
    fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.open(document.getElementById('terminal-container'));
    bindTerminalGestures();
    
    socket = io('/term', { reconnection: true, reconnectionAttempts: 5, reconnectionDelay: 1000 });
    
    socket.on('connect', () => {
        if (isTermOpen) {
            term.write('\r\n\x1b[32m*** 已连接 ***\x1b[0m\r\n');
        }
        socket.emit('create_terminal', { cwd: (_requestedCwd || cwd) });
        fitAddon.fit();
        socket.emit('resize', { cols: term.cols, rows: term.rows });
        setTimeout(() => {
            if (!isTermOpen) return;
            tryRunPendingOpenActions();
        }, 80);
    });

    socket.on('output', (data) => {
        if (isTermOpen) {
            term.write(data.data);
        }
    });

    socket.on('disconnect', () => {
        if (isTermOpen) {
            term.write('\r\n\x1b[33m*** 连接中... ***\x1b[0m\r\n');
        }
    });

    socket.on('connect_error', () => {
        if (isTermOpen) {
            term.write('\r\n\x1b[31m*** 连接失败 ***\x1b[0m\r\n');
        }
    });

    term.onData((data) => {
        if (socket && socket.connected) {
            const out = applyModifiersToData(data);
            socket.emit('input', { input: out });
        }
    });
    
    term.onResize((size) => {
        if (socket && socket.connected) {
            socket.emit('resize', { cols: size.cols, rows: size.rows });
        }
    });
    
    window.addEventListener('resize', () => {
        const drawerEl = document.getElementById('terminalDrawer');
        if (fitAddon && drawerEl && drawerEl.classList.contains('open')) {
            fitAddon.fit();
            if (socket && socket.connected) {
                socket.emit('resize', { cols: term.cols, rows: term.rows });
            }
        }
    });
}

function closeTerminal() {
    isTermOpen = false;
    ctrlMode = false;
    altMode = false;
    syncModifierButtons();
    const drawerEl = document.getElementById('terminalDrawer');
    if (drawerEl) {
        drawerEl.style.bottom = '';
        drawerEl.style.height = '';
        drawerEl.style.maxHeight = '';
    }
    const drawer = document.getElementById('terminalDrawer');
    const backdrop = document.getElementById('terminalBackdrop');
    if (drawer) drawer.classList.remove('open');
    if (backdrop) backdrop.classList.remove('open');
}

// 导出
window.openTerminal = openTerminal;
window.closeTerminal = closeTerminal;
window.termInitialized = termInitialized;
window.handleKeyBtn = handleKeyBtn;
