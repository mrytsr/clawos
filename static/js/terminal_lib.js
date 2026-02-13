/**
 * TerminalLib.js - 可嵌入的终端组件库
 * 
 * 使用方式:
 *   1. 在页面引入此脚本和样式
 *   2. 在页面合适位置添加: <div id="terminal-lib-container"></div>
 *   3. 调用 TerminalLib.open('/path/to/dir') 打开终端
 * 
 * API:
 *   TerminalLib.open(path)    - 打开终端（可选指定目录）
 *   TerminalLib.close()      - 关闭终端
 *   TerminalLib.send(cmd)    - 发送命令
 *   TerminalLib.isOpen()     - 检查是否打开
 */

// 动态加载 xterm 样式（如果页面没有）
(function loadXtermStyle() {
    if (document.querySelector('link[href*="xterm"]')) return;
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/xterm@5.3.0/css/xterm.css';
    document.head.appendChild(link);
})();

var TerminalLib = (function() {
    var _instance = null;
    var _containerId = 'terminal-lib-container';
    var _isInit = false;

    function init() {
        if (_isInit) return;
        _isInit = true;

        // 创建容器
        var container = document.createElement('div');
        container.id = _containerId;
        container.innerHTML = getComponentHTML();
        document.body.appendChild(container);

        // 绑定事件
        bindEvents();
    }

    function getComponentHTML() {
        return '\
<div id="terminal-component" class="term-lib-component" style="display:none;">\
    <div class="term-lib-backdrop" onclick="TerminalLib.close()"></div>\
    <div class="term-lib-drawer">\
        <div class="term-lib-header">\
            <span id="termLibPath" class="term-lib-path">~</span>\
            <button class="term-lib-close" onclick="TerminalLib.close()">×</button>\
        </div>\
        <div class="term-lib-container" id="termLibContainer"></div>\
        <div class="term-lib-toolbar">\
            <button class="term-lib-btn" onclick="TerminalLib.send(\'clear\\r\')">清屏</button>\
            <button class="term-lib-btn" onclick="TerminalLib.focus()">聚焦</button>\
        </div>\
    </div>\
</div>\
<style>\
.term-lib-component {\
    position: fixed; inset: 0; z-index: 2000;\
    display: flex; align-items: center; justify-content: center;\
}\
.term-lib-backdrop {\
    position: absolute; inset: 0; background: rgba(0,0,0,0.6);\
}\
.term-lib-drawer {\
    position: relative; width: 90%; max-width: 900px;\
    height: 60vh; max-height: 500px;\
    background: #000; border-radius: 12px;\
    display: flex; flex-direction: column;\
    overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.6);\
}\
.term-lib-header {\
    padding: 10px 14px; background: #1a1a2e;\
    display: flex; align-items: center; justify-content: space-between;\
}\
.term-lib-path { color: #888; font-size: 13px; font-family: monospace; }\
.term-lib-close {\
    width: 28px; height: 28px; border-radius: 6px;\
    background: #e94560; border: none; color: #fff;\
    cursor: pointer; font-size: 18px;\
}\
.term-lib-close:hover { background: #ff6b6b; }\
.term-lib-container { flex: 1; padding: 8px; overflow: hidden; }\
.term-lib-toolbar { padding: 8px 12px; background: #1a1a2e; display: flex; gap: 8px; }\
.term-lib-btn {\
    padding: 6px 12px; border-radius: 6px;\
    background: #0f3460; border: none; color: #ccc;\
    cursor: pointer; font-size: 12px;\
}\
.term-lib-btn:hover { background: #16213e; }\
</style>';
    }

    function bindEvents() {
        // ESC 关闭
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                var el = document.getElementById('terminal-component');
                if (el && el.style.display !== 'none') {
                    close();
                }
            }
        });
    }

    var term = null;
    var fitAddon = null;
    var socket = null;
    var isOpen = false;
    var cwd = '/root/.openclaw/workspace';

    function createSocket() {
        var s = io('/term', {
            forceNew: true,
            reconnection: true,
            reconnectionAttempts: 3,
            reconnectionDelay: 1000,
            transports: ['websocket', 'polling'],
            upgrade: false
        });

        s.on('connect', function() {
            s.emit('create_terminal', { cwd: cwd });
            if (term) term.write('\r\n\x1b[32m*** 已连接 ***\x1b[0m\r\n');
            if (fitAddon) fitAddon.fit();
            if (s && term) s.emit('resize', { cols: term.cols, rows: term.rows });
        });

        s.on('output', function(data) {
            if (isOpen && term && data && data.data) {
                term.write(data.data);
            }
        });

        s.on('disconnect', function() {
            if (isOpen && term) {
                term.write('\r\n\x1b[33m*** 连接断开 ***\x1b[0m\r\n');
            }
        });

        s.on('connect_error', function() {
            if (isOpen && term) {
                term.write('\r\n\x1b[31m*** 连接失败 ***\x1b[0m\r\n');
            }
        });

        return s;
    }

    function initTerm() {
        if (term) return;

        // 确保 xterm 已加载
        if (typeof Terminal === 'undefined') {
            console.error('xterm.js 未加载');
            return;
        }

        term = new Terminal({
            cursorBlink: true,
            fontSize: 13,
            fontFamily: 'Menlo, Monaco, "Courier New", monospace',
            theme: { background: '#000000' }
        });

        // 确保 FitAddon 已加载
        if (typeof FitAddon === 'undefined') {
            console.error('xterm-addon-fit 未加载');
            return;
        }

        fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);
        term.open(document.getElementById('termLibContainer'));
        fitAddon.fit();

        socket = createSocket();

        term.onData(function(data) {
            if (socket && socket.connected) {
                socket.emit('input', { input: data });
            }
        });

        term.onResize(function(size) {
            if (socket && socket.connected) {
                socket.emit('resize', { cols: size.cols, rows: size.rows });
            }
        });
    }

    function open(path) {
        if (isOpen) return;
        init();

        cwd = path || cwd;
        document.getElementById('terminal-component').style.display = 'flex';
        isOpen = true;

        // 确保 xterm 库已加载
        if (typeof Terminal === 'undefined' || typeof FitAddon === 'undefined') {
            loadXtermLib(function() {
                initTerm();
                doOpen();
            });
        } else {
            initTerm();
            doOpen();
        }
    }

    function doOpen() {
        document.getElementById('termLibPath').textContent = cwd || '~';

        if (socket && !socket.connected) {
            socket.connect();
        }

        setTimeout(function() {
            if (socket && socket.connected && cwd) {
                socket.emit('input', { input: 'cd ' + cwd + '\r' });
            }
        }, 300);

        setTimeout(function() {
            if (term) {
                term.focus();
                if (fitAddon) fitAddon.fit();
            }
        }, 200);
    }

    function close() {
        if (!isOpen) return;
        document.getElementById('terminal-component').style.display = 'none';
        isOpen = false;
    }

    function send(cmd) {
        if (term && socket && socket.connected) {
            socket.emit('input', { input: cmd });
            term.focus();
        }
    }

    function focus() {
        if (term) term.focus();
    }

    function isOpenFn() {
        return isOpen;
    }

    // 动态加载 xterm 库
    function loadXtermLib(callback) {
        if (typeof Terminal !== 'undefined' && typeof FitAddon !== 'undefined') {
            callback();
            return;
        }

        var loaded = { xterm: false, fit: false };
        function checkAndCall() {
            if (loaded.xterm && loaded.fit) callback();
        }

        var script1 = document.createElement('script');
        script1.src = 'https://unpkg.com/xterm@5.3.0/lib/xterm.js';
        script1.onload = function() {
            loaded.xterm = true;
            checkAndCall();
        };
        document.body.appendChild(script1);

        var script2 = document.createElement('script');
        script2.src = 'https://unpkg.com/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js';
        script2.onload = function() {
            loaded.fit = true;
            checkAndCall();
        };
        document.body.appendChild(script2);
    }

    return {
        open: open,
        close: close,
        send: send,
        focus: focus,
        isOpen: isOpenFn
    };
})();
