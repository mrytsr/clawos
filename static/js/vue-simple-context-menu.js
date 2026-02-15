// 修复 Vue 加载顺序问题 - 在加载 vue-simple-context-menu 之前设置好 Vue
(function() {
    // 1. 确保 Vue 存在并有 use 方法
    if (typeof window !== 'undefined') {
        window.Vue = window.Vue || {};
        // 防止 UMD 检查时 Vue.use 不存在
        if (!window.Vue.use) {
            window.Vue.use = function(plugin) {
                // 空实现，只是为了不让 UMD 报错的
                return this;
            };
        }
    }
    
    // 2. 动态加载 vue-simple-context-menu
    var script = document.createElement('script');
    script.src = '/static/lib/vue-simple-context-menu.umd.js';
    script.onload = function() {
        console.log('vue-simple-context-menu loaded, VueSimpleContextMenu:', typeof window.VueSimpleContextMenu);
    };
    script.onerror = function(e) {
        console.error('Failed to load vue-simple-context-menu:', e);
    };
    document.head.appendChild(script);
})();
