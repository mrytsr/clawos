/**
 * I18n - 国际化/多语言支持
 * 支持 zh(中文), en(英文), ja(日文)
 */
(function(global) {
    'use strict';

    var I18n = {
        lang: 'en',
        data: {},
        __loaded: false,
        __observer: null,
        supportedLangs: ['zh', 'en', 'ja'],
        langNames: {
            'zh': '中文',
            'en': 'English',
            'ja': '日本語'
        },

        /**
         * 初始化
         */
        init: function() {
            var savedLang = null;
            try { savedLang = localStorage.getItem('clawos_lang'); } catch (e) {}
            var defaultLang = savedLang || 'en';
            this.setLang(defaultLang);
        },

        /**
         * 设置语言
         */
        setLang: function(lang) {
            if (this.supportedLangs.indexOf(lang) === -1) {
                lang = 'en';
            }
            this.lang = lang;
            try { localStorage.setItem('clawos_lang', lang); } catch (e) {}
            this.loadLang(lang);
        },

        /**
         * 加载语言文件
         */
        loadLang: function(lang) {
            var self = this;
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/static/lang/' + lang + '.json', true);
            xhr.onreadystatechange = function() {
                if (xhr.readyState === 4 && xhr.status === 200) {
                    try {
                        self.data = JSON.parse(xhr.responseText);
                        self.__loaded = true;
                        self.updatePage();
                    } catch(e) {
                        console.error('Failed to parse language file:', e);
                    }
                }
            };
            xhr.send();
        },

        get: function(key) {
            var keys = key.split('.');
            var value = this.data;
            for (var i = 0; i < keys.length; i++) {
                value = value ? value[keys[i]] : null;
            }
            return value === null || typeof value === 'undefined' ? null : value;
        },

        /**
         * 翻译文本
         */
        t: function(key) {
            var value = this.get(key);
            return value === null || typeof value === 'undefined' ? key : value;
        },

        /**
         * 更新页面上的所有翻译文本
         */
        updatePage: function() {
            // 更新 textContent
            var elements = document.querySelectorAll('[data-i18n]');
            for (var i = 0; i < elements.length; i++) {
                var el = elements[i];
                var key = el.getAttribute('data-i18n');
                if (key) {
                    var v = this.get(key);
                    if (v !== null && typeof v !== 'undefined') el.textContent = v;
                }
            }
            // 更新 title 属性
            var titleElements = document.querySelectorAll('[data-i18n-title]');
            for (var j = 0; j < titleElements.length; j++) {
                var elTitle = titleElements[j];
                var titleKey = elTitle.getAttribute('data-i18n-title');
                if (titleKey) {
                    var tv = this.get(titleKey);
                    if (tv !== null && typeof tv !== 'undefined') elTitle.title = tv;
                }
            }
            // 更新 aria-label 属性
            var ariaElements = document.querySelectorAll('[data-i18n-aria-label]');
            for (var a = 0; a < ariaElements.length; a++) {
                var elAria = ariaElements[a];
                var ariaKey = elAria.getAttribute('data-i18n-aria-label');
                if (ariaKey) {
                    var av = this.get(ariaKey);
                    if (av !== null && typeof av !== 'undefined') elAria.setAttribute('aria-label', av);
                }
            }
            // 更新 placeholder 属性
            var placeholderElements = document.querySelectorAll('[data-i18n-placeholder]');
            for (var k = 0; k < placeholderElements.length; k++) {
                var elPlaceholder = placeholderElements[k];
                var placeholderKey = elPlaceholder.getAttribute('data-i18n-placeholder');
                if (placeholderKey) {
                    var pv = this.get(placeholderKey);
                    if (pv !== null && typeof pv !== 'undefined') elPlaceholder.placeholder = pv;
                }
            }
            // 触发语言变更事件
            if (typeof Event !== 'undefined') {
                var event = new CustomEvent('i18n:languageChanged', { detail: { lang: this.lang } });
                document.dispatchEvent(event);
            }
        },

        __applyToSubtree: function(root) {
            if (!this.__loaded) return;
            if (!root) return;
            var selector = '[data-i18n],[data-i18n-title],[data-i18n-aria-label],[data-i18n-placeholder]';
            var translateEl = (function(el) {
                if (!el || el.nodeType !== 1) return;
                var k = el.getAttribute('data-i18n');
                if (k) {
                    var v = this.get(k);
                    if (v !== null && typeof v !== 'undefined') el.textContent = v;
                }
                var tk = el.getAttribute('data-i18n-title');
                if (tk) {
                    var tv = this.get(tk);
                    if (tv !== null && typeof tv !== 'undefined') el.title = tv;
                }
                var ak = el.getAttribute('data-i18n-aria-label');
                if (ak) {
                    var av = this.get(ak);
                    if (av !== null && typeof av !== 'undefined') el.setAttribute('aria-label', av);
                }
                var pk = el.getAttribute('data-i18n-placeholder');
                if (pk) {
                    var pv = this.get(pk);
                    if (pv !== null && typeof pv !== 'undefined') el.placeholder = pv;
                }
            }).bind(this);

            if (root.nodeType === 1) translateEl(root);
            if (root.querySelectorAll) {
                var nodes = root.querySelectorAll(selector);
                for (var i = 0; i < nodes.length; i++) translateEl(nodes[i]);
            }
        },

        __ensureObserver: function() {
            if (this.__observer) return;
            if (typeof MutationObserver === 'undefined') return;
            var self = this;
            this.__observer = new MutationObserver(function(mutations) {
                if (!self.__loaded) return;
                for (var i = 0; i < mutations.length; i++) {
                    var m = mutations[i];
                    if (!m || !m.addedNodes) continue;
                    for (var j = 0; j < m.addedNodes.length; j++) {
                        var n = m.addedNodes[j];
                        if (!n) continue;
                        if (n.nodeType === 1 || n.nodeType === 11) self.__applyToSubtree(n);
                    }
                }
            });
            this.__observer.observe(document.documentElement, { childList: true, subtree: true });
        },

        /**
         * 获取当前语言名称
         */
        getCurrentLangName: function() {
            return this.langNames[this.lang] || this.lang;
        },

        /**
         * 获取支持的语言列表
         */
        getSupportedLangs: function() {
            return this.supportedLangs.map(function(code) {
                return { code: code, name: I18n.langNames[code] };
            });
        }
    };

    // 导出到全局
    global.I18n = I18n;

    (function boot() {
        if (I18n.__booted) return;
        I18n.__booted = true;
        I18n.init();
        var onReady = function() {
            I18n.__ensureObserver();
            if (I18n.__loaded) I18n.updatePage();
        };
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', onReady);
        } else {
            onReady();
        }
    })();

})(typeof window !== 'undefined' ? window : this);
