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
     * @property {string[]} paths - The relative paths of the source files
     * @property {number} count - Number of files
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
        var bar = document.getElementById('clipboardBar');
        if (!bar) {
            bar = document.createElement('div');
            bar.id = 'clipboardBar';
            document.body.appendChild(bar);
        }

        bar.className = 'clipboard-bar';
        bar.setAttribute('role', 'region');
        bar.setAttribute('aria-label', typeof I18n !== 'undefined' ? I18n.t('clipboard.title') : 'Clipboard Operations');
        if (!bar.getAttribute('aria-hidden')) bar.setAttribute('aria-hidden', 'true');

        if (bar.getAttribute('data-clipboard-initialized') !== '1') {
            bar.innerHTML =
                '<div class="clipboard-main">' +
                    '<div class="clipboard-text">' +
                        '<div id="clipboardTitle" class="clipboard-title"></div>' +
                        '<div id="clipboardFilename" class="clipboard-filename"></div>' +
                    '</div>' +
                    '<div class="clipboard-actions">' +
                    '<button id="clipboardPasteBtn" type="button" class="clipboard-paste-btn" aria-label="' + (typeof I18n !== 'undefined' ? I18n.t('common.paste') : 'Paste') + '">' + (typeof I18n !== 'undefined' ? I18n.t('common.paste') : 'Paste') + '</button>' +
                    '<button id="clipboardCloseBtn" type="button" class="clipboard-close-btn" aria-label="' + (typeof I18n !== 'undefined' ? I18n.t('common.close') : 'Close') + '">×</button>' +

                    '</div>' +
                '</div>';

            bar.setAttribute('data-clipboard-initialized', '1');
        }

        var pasteBtn = document.getElementById('clipboardPasteBtn');
        var closeBtn = document.getElementById('clipboardCloseBtn');

        if (pasteBtn && pasteBtn.getAttribute('data-clipboard-bound') !== '1') {
            pasteBtn.addEventListener('click', debounce(function() {
                pasteHere();
            }, PASTE_DEBOUNCE_MS));
            pasteBtn.setAttribute('data-clipboard-bound', '1');
        }
        if (closeBtn && closeBtn.getAttribute('data-clipboard-bound') !== '1') {
            closeBtn.addEventListener('click', function() {
                cancel();
            });
            closeBtn.setAttribute('data-clipboard-bound', '1');
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
                bar.style.display = 'none';
                bar.setAttribute('aria-hidden', 'true');
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
            if (!parsed || !parsed.type) return null;
            
            // Normalize legacy format (single path) to array
            var paths = [];
            if (parsed.paths && Array.isArray(parsed.paths)) {
                paths = parsed.paths;
            } else if (parsed.path) {
                paths = [parsed.path];
            } else {
                return null;
            }

            return {
                op: parsed.type,
                paths: paths,
                count: paths.length,
                ts: parsed.ts || nowMs()
            };
        } catch (e) {
            console.warn('Clipboard read failed', e);
            return null;
        }
    }

    /**
     * Write state to storage
     * @param {'copy'|'cut'} op 
     * @param {string|string[]|Object|Object[]} items - Single path, array of paths, single item object, or array of item objects
     * @returns {boolean}
     */
    function set(op, items) {
        if (typeof window === 'undefined' || !window.localStorage) return false;
        try {
            var paths = [];
            
            // Handle different input types
            if (Array.isArray(items)) {
                paths = items.map(function(item) {
                    return (typeof item === 'string') ? item : item.path;
                }).filter(Boolean);
            } else if (typeof items === 'string') {
                paths = [items];
            } else if (items && items.path) {
                paths = [items.path];
            }

            if (paths.length === 0) return false;

            var state = {
                type: op,
                paths: paths,
                count: paths.length,
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
        var titleEl = document.getElementById('clipboardTitle');
        var filenameEl = document.getElementById('clipboardFilename');
        
        if (bar && filenameEl) {
            var titleText;
            if (state.op === 'link') {
                titleText = typeof I18n !== 'undefined' ? I18n.t('clipboard.link_selected') : 'Link selected';
            } else if (state.op === 'cut') {
                titleText = typeof I18n !== 'undefined' ? I18n.t('clipboard.cut') : 'Cut to clipboard';
            } else {
                titleText = typeof I18n !== 'undefined' ? I18n.t('clipboard.copied') : 'Copied to clipboard';
            }
            if (titleEl) {
                titleEl.textContent = titleText;
            }
            var fileText = '';
            if (state.count === 1) {
                fileText = state.paths[0].split(/[/\\]/).pop();
            } else {
                fileText = state.count + (typeof I18n !== 'undefined' ? I18n.t('clipboard.items_count') : ' items');
            }
            filenameEl.textContent = fileText;
            bar.style.display = 'flex';
            bar.setAttribute('aria-hidden', 'false');
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

        var currentPathInput = document.getElementById('currentBrowsePath');
        var targetDir = currentPathInput ? currentPathInput.value : '';

        var endpoint, payload;
        if (state.op === 'link') {
            endpoint = '/api/batch/symlink';
            payload = {
                paths: state.paths,
                target: targetDir
            };
        } else if (state.op === 'cut') {
            endpoint = '/api/batch/move';
            payload = {
                paths: state.paths,
                target: targetDir
            };
        } else {
            endpoint = '/api/batch/copy';
            payload = {
                paths: state.paths,
                target: targetDir
            };
        }

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
                clear();
                removeDom();
                if (window.showToast) {
                    var msg = '';
                    var itemsLabel = typeof I18n !== 'undefined' ? I18n.t('clipboard.items_count_suffix') : 'items';
                    if (state.count === 1) {
                        var name = state.paths[0].split(/[/\\]/).pop();
                        if (state.op === 'link') {
                            msg = (typeof I18n !== 'undefined' ? I18n.t('clipboard.link_created') : 'Link created') + ': ' + name;
                        } else if (state.op === 'cut') {
                            msg = (typeof I18n !== 'undefined' ? I18n.t('clipboard.moved') : 'Moved') + ': ' + name;
                        } else {
                            msg = (typeof I18n !== 'undefined' ? I18n.t('clipboard.copied') : 'Copied to clipboard') + ': ' + name;
                        }
                    } else {
                        if (state.op === 'link') {
                            msg = (typeof I18n !== 'undefined' ? I18n.t('clipboard.link_created') : 'Link created') + ' ' + state.count + ' ' + itemsLabel;
                        } else if (state.op === 'cut') {
                            msg = (typeof I18n !== 'undefined' ? I18n.t('clipboard.moved') : 'Moved') + ' ' + state.count + ' ' + itemsLabel;
                        } else {
                            msg = (typeof I18n !== 'undefined' ? I18n.t('clipboard.copied') : 'Copied to clipboard') + ' ' + state.count + ' ' + itemsLabel;
                        }
                    }
                    window.showToast(msg, 'success');
                }
                if (window.refreshFileList) {
                    window.refreshFileList();
                }
            } else {
                if (window.showToast) {
                    var errMsg = (data && data.error && data.error.message) || data.message || (typeof I18n !== 'undefined' ? I18n.t('common.unknown_error') : 'Unknown error');
                    window.showToast((typeof I18n !== 'undefined' ? I18n.t('clipboard.operation_failed') : 'Operation failed') + ': ' + errMsg, 'error');
                }
            }
        })
        .catch(function(err) {
            console.error('Paste error:', err);
            if (window.showToast) {
                window.showToast(typeof I18n !== 'undefined' ? I18n.t('common.network_error') : 'Network error', 'error');
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

    if (typeof document !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }
    }

    return {
        set: set,
        write: set,
        read: read,
        clear: clear,
        show: show,
        cancel: cancel,
        pasteHere: pasteHere
    };
});
