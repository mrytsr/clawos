// Vue 3 全局构建兼容性修复
(function() {
    // 在加载 vue-simple-context-menu 之前给 Vue 添加 use 方法
    if (window.Vue && !window.Vue.use) {
        var installedPlugins = [];
        window.Vue.use = function(plugin) {
            var args = Array.prototype.slice.call(arguments, 1);
            if (installedPlugins.indexOf(plugin) !== -1) {
                return this;
            }
            if (plugin.install) {
                plugin.install.apply(plugin, [this].concat(args));
            } else if (typeof plugin === 'function') {
                plugin.apply(null, [this].concat(args));
            }
            installedPlugins.push(plugin);
            return this;
        };
    }
})();
