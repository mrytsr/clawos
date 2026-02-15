// 自定义右键菜单 - 类似 vue-simple-context-menu 的效果
(function() {
    'use strict';
    
    var currentMenu = null;
    var menuElement = null;
    
    function createMenu() {
        if (menuElement) return menuElement;
        
        menuElement = document.createElement('div');
        menuElement.className = 'vue-simple-context-menu';
        menuElement.style.display = 'none';
        menuElement.style.position = 'fixed';
        menuElement.style.zIndex = '10000';
        document.body.appendChild(menuElement);
        
        // 点击其他地方关闭菜单
        document.addEventListener('click', function(e) {
            if (menuElement && !menuElement.contains(e.target)) {
                hideMenu();
            }
        });
        
        return menuElement;
    }
    
    function showMenu(event, item, options) {
        var menu = createMenu();
        
        // 保存当前项
        window.__contextMenuItem = item;
        window.currentItemPath = item.path || '';
        window.currentItemName = item.name || '';
        window.currentItemIsDir = !!item.is_dir;
        
        // 生成菜单 HTML
        var html = '';
        options.forEach(function(opt) {
            if (opt.type === 'divider') {
                html += '<div class="vue-simple-context-menu__divider"></div>';
            } else {
                html += '<div class="vue-simple-context-menu__item" data-action="' + opt.slug + '">' + opt.name + '</div>';
            }
        });
        
        menu.innerHTML = html;
        
        // 添加点击事件
        menu.querySelectorAll('.vue-simple-context-menu__item').forEach(function(el) {
            el.addEventListener('click', function() {
                var action = this.dataset.action;
                hideMenu();
                if (typeof window.handleMenuAction === 'function') {
                    window.handleMenuAction(action);
                }
            });
        });
        
        // 定位菜单
        var x = event.pageX;
        var y = event.pageY;
        
        // 确保菜单不超出视口
        var menuRect = menu.getBoundingClientRect();
        if (x + menuRect.width > window.innerWidth) {
            x = window.innerWidth - menuRect.width - 10;
        }
        if (y + menuRect.height > window.innerHeight) {
            y = window.innerHeight - menuRect.height - 10;
        }
        
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';
        menu.style.display = 'block';
        
        currentMenu = menu;
        
        event.preventDefault();
        event.stopPropagation();
    }
    
    function hideMenu() {
        if (menuElement) {
            menuElement.style.display = 'none';
        }
        currentMenu = null;
    }
    
    // 导出到全局
    window.showCustomContextMenu = showMenu;
    window.hideCustomContextMenu = hideMenu;
    
})();
