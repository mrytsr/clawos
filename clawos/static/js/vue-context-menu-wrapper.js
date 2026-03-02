// 创建包装组件来暴露 showMenu 方法
(function() {
    // 等待 Vue 加载
    function init() {
        if (!window.Vue || !window.VueSimpleContextMenu) {
            setTimeout(init, 100);
            return;
        }
        
        // 创建包装组件
        var ContextMenuWrapper = {
            extends: window.VueSimpleContextMenu,
            expose: ['showMenu'],
            methods: {
                showMenu: function(event, item) {
                    // 调用父类的 showMenu
                    this.$super && this.$super.showMenu(event, item);
                }
            }
        };
        
        // 替换原组件
        window.VueSimpleContextMenu = ContextMenuWrapper;
        console.log('Context menu wrapper created');
    }
    
    init();
})();
