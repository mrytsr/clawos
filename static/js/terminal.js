// ============ 终端功能模块 ============

let term = null;
let fitAddon = null;
let socket = null;
let termInitialized = false;
let isTermOpen = false;

function openTerminal(path, isDir) {
    closeMenuModal();
    if (typeof window !== 'undefined' && window.SERVER_IS_WINDOWS) {
        showToast('服务端环境不支持 Web 终端（需要 Linux PTY/termios）', 'warning');
        return;
    }
    isTermOpen = true;
    
    // 计算路径
    let termPath = '/root/.openclaw/workspace';
    if (path) {
        if (isDir) {
            termPath = '/root/.openclaw/workspace/' + path;
        } else {
            const lastSlash = path.lastIndexOf('/');
            termPath = lastSlash > 0 ? '/root/.openclaw/workspace/' + path.substring(0, lastSlash) : '/root/.openclaw/workspace';
        }
    }
    
    const pathEl = document.getElementById('termPath');
    if (pathEl) pathEl.textContent = termPath;
    
    const drawer = document.getElementById('terminalDrawer');
    const backdrop = document.getElementById('terminalBackdrop');
    
    if (drawer) drawer.classList.add('open');
    if (backdrop) backdrop.classList.add('open');
    
    if (!termInitialized) {
        initTerminal(termPath);
        termInitialized = true;
    } else if (socket) {
        socket.disconnect();
        socket.connect();
    }
    
    setTimeout(() => {
        if (fitAddon) {
            fitAddon.fit();
            if (socket && socket.connected) {
                socket.emit('resize', { cols: term.cols, rows: term.rows });
            }
        }
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
    
    socket = io('/term', { reconnection: true, reconnectionAttempts: 5, reconnectionDelay: 1000 });
    
    socket.on('connect', () => {
        if (isTermOpen) {
            term.write('\r\n\x1b[32m*** 已连接 ***\x1b[0m\r\n');
        }
        socket.emit('create_terminal', { cwd: cwd });
        fitAddon.fit();
        socket.emit('resize', { cols: term.cols, rows: term.rows });
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
            socket.emit('input', { input: data });
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
    const drawer = document.getElementById('terminalDrawer');
    const backdrop = document.getElementById('terminalBackdrop');
    if (drawer) drawer.classList.remove('open');
    if (backdrop) backdrop.classList.remove('open');
    if (socket) {
        socket.disconnect();
    }
}

// 导出
window.openTerminal = openTerminal;
window.closeTerminal = closeTerminal;
window.termInitialized = termInitialized;
