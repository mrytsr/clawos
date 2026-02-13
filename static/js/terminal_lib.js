/**
 * TerminalLib.js - 可嵌入的终端组件库
 * 
 * 使用方式:
 *   1. 在页面引入此脚本
 *   2. 调用 TerminalLib.open('/path/to/dir') 打开终端
 * 
 * API:
 *   TerminalLib.open(path)    - 打开终端（可选指定目录）
 *   TerminalLib.close()       - 关闭终端
 *   TerminalLib.send(cmd)     - 发送命令
 *   TerminalLib.focus()       - 聚焦终端
 *   TerminalLib.isOpen()      - 检查是否打开
 */

// 动态加载 xterm 样式
(function loadXtermStyle() {
    if (document.querySelector('link[href*="xterm"]')) return;
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/xterm@5.3.0/css/xterm.css';
    document.head.appendChild(link);
})();

var TerminalLib = (function() {
    var _isInit = false;
    var term = null;
    var fitAddon = null;
    var socket = null;
    var isOpen = false;
    var cwd = '/root/.openclaw/workspace';
    var ctrlMode = false;
    var altMode = false;

    function getComponentHTML() {
        return '\
<div id="term-lib-component" class="term-lib-component" style="display:none;">\
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
            <button class="term-lib-btn" onclick="TerminalLib.toggleKeyboard()">⌨️ 键盘</button>\
        </div>\
        <div class="term-lib-keyboard" id="termLibKeyboard">\
            <div class="term-key-row">\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event, \'esc\')">ESC</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event, \'tab\')">TAB</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event, \'home\')">HOME</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event, \'end\')">END</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event, \'pgup\')">PGUP</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event, \'pgdn\')">PGDN</button>\
            </div>\
            <div class="term-key-row">\
                <button class="term-key" data-mod="ctrl" onmousedown="TerminalLib.handleKey(event, \'ctrl\')">CTRL</button>\
                <button class="term-key" data-mod="alt" onmousedown="TerminalLib.handleKey(event, \'alt\')">ALT</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event, \'up\')">↑</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event, \'down\')">↓</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event, \'left\')">←</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event, \'right\')">→</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event, \'enter\')">↵</button>\
            </div>\
        </div>\
    </div>\
</div>\
<style>\
.term-lib-component {\
    position: fixed; inset: 0; z-index: 2000;\
    display: flex; align-items: center; justify-content: center;\
}\
.term-lib-backdrop { position: absolute; inset: 0; background: rgba(0,0,0,0.6); }\
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
    background: #e94560; border: none; color: #fff; cursor: pointer; font-size: 18px;\
}\
.term-lib-container { flex: 1; padding: 8px; overflow: hidden; }\
.term-lib-toolbar { padding: 8px 12px; background: #1a1a2e; display: flex; gap: 8px; }\
.term-lib-btn {\
    padding: 6px 12px; border-radius: 6px;\
    background: #0f3460; border: none; color: #ccc; cursor: pointer; font-size: 12px;\
}\
.term-lib-btn:hover { background: #16213e; }\
.term-lib-keyboard {\
    padding: 8px 12px; background: #1a1a2e; border-top: 1px solid #333;\
    display: none; flex-direction: column; gap: 6px;\
}\
.term-lib-keyboard.visible { display: flex; }\
.term-key-row { display: flex; gap: 6px; justify-content: center; }\
.term-key {\
    padding: 8px 12px; min-width: 40px; border-radius: 6px;\
    background: #0f3460; border: none; color: #ccc; cursor: pointer; font-size: 12px;\
}\
.term-key:hover { background: #16213e; }\
.term-key.active { background: #0969da !important; color: #fff; }\
</style>';
    }

    function init() {
        if (_isInit) return;
        _isInit = true;

        var div = document.createElement('div');
        div.innerHTML = getComponentHTML();
        document.body.appendChild(div);

        // ESC 关闭
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                var el = document.getElementById('term-lib-component');
                if (el && el.style.display !== 'none') {
                    close();
                }
            }
        });
    }

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

        return s;
    }

    function initTerm() {
        if (term) return;

        term = new Terminal({
            cursorBlink: true,
            fontSize: 13,
            fontFamily: 'Menlo, Monaco, "Courier New", monospace',
            theme: { background: '#000000' }
        });

        fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);
        term.open(document.getElementById('termLibContainer'));
        fitAddon.fit();

        socket = createSocket();

        term.onData(function(data) {
            if (socket && socket.connected) {
                socket.emit('input', { input: applyModifiers(data) });
            }
        });

        term.onResize(function(size) {
            if (socket && socket.connected) {
                socket.emit('resize', { cols: size.cols, rows: size.rows });
            }
        });
    }

    function keySeq(key) {
        var map = {
            'esc': '\x1b', 'enter': '\r', 'tab': '\t',
            'up': '\x1b[A', 'down': '\x1b[B', 'left': '\x1b[D', 'right': '\x1b[C',
            'home': '\x1b[H', 'end': '\x1b[F', 'pgup': '\x1b[5~', 'pgdn': '\x1b[6~',
            'backspace': '\x7f', 'slash': '/', 'dash': '-'
        };
        return map[key] || key;
    }

    function applyModifiers(data) {
        if (!data) return '';
        var first = data[0];

        if (ctrlMode) {
            var c = String(first).toLowerCase();
            var code = c.charCodeAt(0);
            if (code >= 97 && code <= 122) {
                data = String.fromCharCode(code - 96);
            }
            ctrlMode = false;
            altMode = false;
            syncButtons();
            return data;
        }

        if (altMode) {
            altMode = false;
            syncButtons();
            return '\x1b' + data;
        }

        return data;
    }

    function syncButtons() {
        var ctrlBtn = document.querySelector('.term-key[data-mod="ctrl"]');
        var altBtn = document.querySelector('.term-key[data-mod="alt"]');
        if (ctrlBtn) ctrlBtn.classList.toggle('active', ctrlMode);
        if (altBtn) altBtn.classList.toggle('active', altMode);
    }

    function open(path) {
        if (isOpen) return;
        init();

        cwd = path || cwd;
        document.getElementById('term-lib-component').style.display = 'flex';
        isOpen = true;

        // 加载 xterm 库
        if (typeof Terminal === 'undefined' || typeof FitAddon === 'undefined') {
            var loaded = { xterm: false, fit: false };
            function check() {
                if (loaded.xterm && loaded.fit) doOpen();
            }
            var s1 = document.createElement('script');
            s1.src = 'https://unpkg.com/xterm@5.3.0/lib/xterm.js';
            s1.onload = function() { loaded.xterm = true; check(); };
            document.body.appendChild(s1);
            var s2 = document.createElement('script');
            s2.src = 'https://unpkg.com/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js';
            s2.onload = function() { loaded.fit = true; check(); };
            document.body.appendChild(s2);
        } else {
            doOpen();
        }
    }

    function doOpen() {
        document.getElementById('termLibPath').textContent = cwd || '~';

        if (!term) {
            initTerm();
        } else if (socket && !socket.connected) {
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
        document.getElementById('term-lib-component').style.display = 'none';
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

    function toggleKeyboard() {
        var kb = document.getElementById('termLibKeyboard');
        kb.classList.toggle('visible');
    }

    function handleKey(e, key) {
        e.preventDefault();
        e.stopPropagation();

        if (key === 'ctrl') {
            ctrlMode = !ctrlMode;
            if (ctrlMode && altMode) altMode = false;
            syncButtons();
            focus();
            return;
        }

        if (key === 'alt') {
            altMode = !altMode;
            if (altMode && ctrlMode) ctrlMode = false;
            syncButtons();
            focus();
            return;
        }

        var seq = keySeq(key);
        if (seq) {
            send(seq);
        }
        focus();
    }

    return {
        open: open,
        close: close,
        send: send,
        focus: focus,
        toggleKeyboard: toggleKeyboard,
        handleKey: handleKey,
        isOpen: function() { return isOpen; }
    };
})();
