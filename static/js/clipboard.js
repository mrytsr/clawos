(function(root, factory) {
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = factory();
    } else {
        root.Clipboard = factory();
    }
})(typeof window !== 'undefined' ? window : globalThis, function() {
    /**
     * @typedef {Object} ClipboardState
     * @property {'copy'|'cut'} op - The operation type
     * @property {string} path - The relative path of the source file
     * @property {string} name - The filename of the source file
     * @property {boolean} isDir - Whether the source is a directory
     * @property {number} ts - Timestamp
     */

    var STORAGE_KEY = 'clipboard_file_path';
    var PASTE_DEBOUNCE_MS = 200;

    /**
     * Helper to get current time
     * @returns {number}
     */
    function nowMs() {
        return Date.now ? Date.now() : new Date().getTime();
    }

    /**
     * Debounce function
     * @param {Function} func 
     * @param {number} wait 
     * @returns {Function}
     */
    function debounce(func, wait) {
        var timeout;
        return function() {
            var context = this;
            var args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                func.apply(context, args);
            }, wait);
        };
    }

    /**
     * Safe JSON parse
     * @param {string} text 
     * @returns {Object|null}
     */
    function safeJsonParse(text) {
        try {
            return JSON.parse(text);
        } catch (e) {
            return null;
        }
    }

    /**
     * Create the DOM elements for the floating bar
     */
    function createDom() {
        if (typeof document === 'undefined') return;
        if (document.getElementById('clipboardBar')) return;

        var bar = document.createElement('div');
        bar.id = 'clipboardBar';
        bar.className = 'clipboard-bar';
        bar.setAttribute('role', 'dialog');
        bar.setAttribute('aria-label', 'Clipboard actions');
        
        // Use SVG for paste icon to avoid external font dependencies
        var pasteIconSvg = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" style="display:block"><path d="M19 2h-4.18C14.4.84 13.3 0 12 0c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm7 18H5V4h2v3h10V4h2v16z"/></svg>';

        bar.innerHTML = 
            '<div id="clipboardFilename" class="clipboard-filename"></div>' +
            '<div class="clipboard-actions">' +
                '<button id="clipboardPasteBtn" class="clipboard-paste-btn">' +
                    pasteIconSvg +
                    '<span>粘贴</span>' +
                '</button>' +
                '<button id="clipboardCancelBtn" class="clipboard-cancel-btn" title="取消" aria-label="Cancel">×</button>' +
            '</div>';

        document.body.appendChild(bar);

        // Bind events
        var pasteBtn = document.getElementById('clipboardPasteBtn');
        var cancelBtn = document.getElementById('clipboardCancelBtn');

        if (pasteBtn) {
            pasteBtn.addEventListener('click', debounce(function() {
                pasteHere();
            }, PASTE_DEBOUNCE_MS));
        }
        if (cancelBtn) {
            cancelBtn.addEventListener('click', function() {
                cancel();
            });
        }
    }

    /**
     * Remove the DOM elements
     */
    function removeDom() {
        if (typeof document === 'undefined') return;
        var bar = document.getElementById('clipboardBar');
        if (bar) {
            bar.classList.remove('visible');
            setTimeout(function() {
                if (bar.parentNode) bar.parentNode.removeChild(bar);
            }, 200); // Wait for fade out
        }
    }

    /**
     * Read state from storage
     * @returns {ClipboardState|null}
     */
    function read() {
        if (typeof window === 'undefined' || !window.localStorage) return null;
        try {
            var raw = window.localStorage.getItem(STORAGE_KEY);
            if (!raw) return null;
            var parsed = safeJsonParse(raw);
            if (!parsed || !parsed.path || !parsed.type) return null;
            
            // Normalize
            return {
                op: parsed.type, // User requested 'type' in requirements, mapping to op
                path: parsed.path,
                name: parsed.name || parsed.path.split(/[/\\]/).pop(),
                isDir: !!parsed.isDir,
                ts: parsed.ts || nowMs()
            };
        } catch (e) {
            console.warn('Clipboard read failed', e);
            return null;
        }
    }

    /**
     * Write state to storage
     * @param {string} op 
     * @param {string} path 
     * @returns {boolean}
     */
    function write(op, path) {
        if (typeof window === 'undefined' || !window.localStorage) return false;
        try {
            var state = {
                type: op,
                path: path,
                name: path.split(/[/\\]/).pop(),
                ts: nowMs()
            };
            window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
            show();
            return true;
        } catch (e) {
            console.warn('Clipboard write failed', e);
            return false;
        }
    }

    /**
     * Clear storage
     */
    function clear() {
        if (typeof window === 'undefined' || !window.localStorage) return;
        try {
            window.localStorage.removeItem(STORAGE_KEY);
        } catch (e) {
            console.warn('Clipboard clear failed', e);
        }
    }

    /**
     * Show the clipboard bar
     */
    function show() {
        var state = read();
        if (!state) return;
        
        createDom();
        var bar = document.getElementById('clipboardBar');
        var filenameEl = document.getElementById('clipboardFilename');
        
        if (bar && filenameEl) {
            filenameEl.textContent = '在此粘贴 ' + state.name;
            // Force reflow
            void bar.offsetWidth;
            bar.classList.add('visible');
        }
    }

    /**
     * Cancel operation
     */
    function cancel() {
        clear();
        removeDom();
    }

    /**
     * Execute paste
     */
    function pasteHere() {
        var state = read();
        if (!state) {
            console.warn('No clipboard state found');
            return;
        }

        // Get current path from DOM (assuming input#currentBrowsePath exists)
        var currentPathInput = document.getElementById('currentBrowsePath');
        var targetDir = currentPathInput ? currentPathInput.value : '';

        // Construct API payload
        var endpoint = state.op === 'cut' ? '/api/batch/move' : '/api/batch/copy';
        var payload = {
            paths: [state.path],
            target: targetDir
        };

        fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                if (state.op === 'cut') {
                    clear();
                    removeDom();
                }
                // Show toast
                if (window.showToast) {
                    window.showToast((state.op === 'cut' ? '已移动: ' : '已复制: ') + state.name, 'success');
                }
                // Refresh list
                if (window.refreshFileList) {
                    window.refreshFileList();
                }
            } else {
                // Keep bar, show error
                if (window.showToast) {
                    window.showToast('操作失败: ' + (data.message || '未知错误'), 'error');
                }
                // Also show snackbar if available (using showToast as snackbar proxy)
            }
        })
        .catch(function(err) {
            console.error('Paste error:', err);
            if (window.showToast) {
                window.showToast('网络错误', 'error');
            }
        });
    }

    /**
     * Initialize
     */
    function init() {
        var state = read();
        if (state) {
            show();
        }
    }

    // Auto init on load
    if (typeof document !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }
    }

    return {
        write: write,
        read: read,
        clear: clear,
        show: show,
        cancel: cancel,
        pasteHere: pasteHere
    };
});
