/**
 * I18n - 国际化/多语言支持
 * 支持 zh(中文), en(英文), ja(日文)
 */
(function(global) {
    'use strict';

    var I18n = {
        lang: 'zh',
        data: {},
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
            var savedLang = localStorage.getItem('clawos_lang');
            var defaultLang = savedLang || 'zh';
            this.setLang(defaultLang);
        },

        /**
         * 设置语言
         */
        setLang: function(lang) {
            if (this.supportedLangs.indexOf(lang) === -1) {
                lang = 'zh';
            }
            this.lang = lang;
            localStorage.setItem('clawos_lang', lang);
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
                        self.updatePage();
                    } catch(e) {
                        console.error('Failed to parse language file:', e);
                    }
                }
            };
            xhr.send();
        },

        /**
         * 翻译文本
         */
        t: function(key) {
            var keys = key.split('.');
            var value = this.data;
            for (var i = 0; i < keys.length; i++) {
                value = value ? value[keys[i]] : null;
            }
            return value || key;
        },

        /**
         * 更新页面上的所有翻译文本
         */
        updatePage: function() {
            var elements = document.querySelectorAll('[data-i18n]');
            for (var i = 0; i < elements.length; i++) {
                var el = elements[i];
                var key = el.getAttribute('data-i18n');
                if (key) {
                    el.textContent = this.t(key);
                }
            }
            // 触发语言变更事件
            if (typeof Event !== 'undefined') {
                var event = new CustomEvent('i18n:languageChanged', { detail: { lang: this.lang } });
                document.dispatchEvent(event);
            }
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

    // DOM 加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            I18n.init();
        });
    } else {
        I18n.init();
    }

})(typeof window !== 'undefined' ? window : this);
