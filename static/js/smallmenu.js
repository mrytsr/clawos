/**
 * SmallMenu - 通用下拉菜单库
 * 支持初始化配置、遮罩层、外部点击关闭等功能
 */
(function(global) {
    'use strict';

    var SmallMenu = {
        _instanceId: 0,
        _menus: {},
        _clickListenerAdded: false,

        /**
         * 初始化并渲染一个菜单
         * @param {Object} options 配置选项
         * @returns {string} 菜单ID
         */
        init: function(options) {
            var self = this;
            var id = options.menuId || ('smallmenu-' + (++this._instanceId));
            var triggerText = options.triggerText || '⋮';
            var triggerClass = options.triggerClass || '';
            var items = options.items || [];
            var onAction = options.onAction || function() {};
            var closeOnMask = options.closeOnMask !== false;
            var closeOnClickOutside = options.closeOnClickOutside !== false;
            var menuClass = options.menuClass || '';

            // 保存菜单配置
            this._menus[id] = {
                items: items,
                onAction: onAction,
                closeOnMask: closeOnMask,
                closeOnClickOutside: closeOnClickOutside
            };

            // 生成菜单HTML
            var menuHtml = '<div class="smallmenu-wrapper" style="position:relative;display:inline-block;">'
                + '<button type="button" class="smallmenu-trigger ' + triggerClass + '" '
                + 'onclick="SmallMenu.toggle(\'' + id + '\')" '
                + 'style="border:none;background:none;cursor:pointer;padding:4px;font-size:16px;line-height:1;">'
                + triggerText
                + '</button>'
                + '<div id="' + id + '" class="smallmenu-dropdown ' + menuClass + '" '
                + 'style="display:none;position:absolute;right:0;top:100%;background:#fff;'
                + 'border:1px solid #d0d7de;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);'
                + 'min-width:140px;z-index:1000;overflow:hidden;">';

            items.forEach(function(item, index) {
                var icon = item.icon || '';
                var label = item.label || '';
                var action = item.action;
                var actionParams = item.actionParams;
                var danger = item.danger ? 'color:#cf222e;' : '';
                var disabled = item.disabled ? 'opacity:0.5;pointer-events:none;' : '';
                var itemId = id + '-item-' + index;

                // 保存 action 和 params 到菜单数据中
                if (!self._menuItems) self._menuItems = {};
                self._menuItems[itemId] = { action: action, actionParams: actionParams };

                // 如果 action 是 function，HTML 中不需要显示
                var actionStr = (typeof action === 'function') ? '' : SmallMenu._escapeHtml(String(action || ''));

                menuHtml += '<div class="smallmenu-item" '
                    + 'data-item-id="' + itemId + '" '
                    + (actionStr ? 'data-action="' + actionStr + '" ' : '')
                    + 'onclick="SmallMenu._handleClick(\'' + id + '\', \'' + itemId + '\')" '
                    + 'style="padding:8px 12px;cursor:pointer;font-size:13px;' + danger + disabled + '">'
                    + (icon ? icon + ' ' : '') + SmallMenu._escapeHtml(label)
                    + '</div>';
            });

            menuHtml += '</div></div>';

            // 添加全局点击监听（只添加一次）
            if (!this._clickListenerAdded) {
                this._setupGlobalClickListener();
                this._clickListenerAdded = true;
            }

            return {
                id: id,
                html: menuHtml
            };
        },

        /**
         * 渲染菜单并返回HTML（便捷方法）
         */
        render: function(options) {
            var result = this.init(options);
            return result.html;
        },

        /**
         * 切换菜单显示/隐藏
         */
        toggle: function(menuId) {
            var menu = document.getElementById(menuId);
            if (!menu) return;

            var menuData = this._menus[menuId];
            if (!menuData) return;

            // 关闭其他菜单
            var allMenus = document.querySelectorAll('.smallmenu-dropdown');
            allMenus.forEach(function(m) {
                if (m.id !== menuId) m.style.display = 'none';
            });

            // 切换当前菜单
            menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
        },

        /**
         * 打开菜单
         */
        open: function(menuId) {
            var menu = document.getElementById(menuId);
            if (menu) {
                // 关闭其他菜单
                var allMenus = document.querySelectorAll('.smallmenu-dropdown');
                allMenus.forEach(function(m) {
                    if (m.id !== menuId) m.style.display = 'none';
                });
                menu.style.display = 'block';
            }
        },

        /**
         * 关闭菜单
         */
        close: function(menuId) {
            var menu = document.getElementById(menuId);
            if (menu) {
                menu.style.display = 'none';
            }
        },

        /**
         * 关闭所有菜单
         */
        closeAll: function() {
            document.querySelectorAll('.smallmenu-dropdown').forEach(function(menu) {
                menu.style.display = 'none';
            });
        },

        /**
         * 处理菜单项点击
         */
        _handleClick: function(menuId, itemId) {
            var self = this;
            var menuData = this._menus[menuId];
            var itemData = this._menuItems ? this._menuItems[itemId] : null;

            if (!itemData) return;

            var action = itemData.action;
            var actionParams = itemData.actionParams;

            // 如果 action 是 function，直接调用
            if (typeof action === 'function') {
                action(actionParams);
            } else if (menuData && menuData.onAction) {
                // 否则调用 onAction 回调
                menuData.onAction(action, actionParams, menuData.items);
            }
            // 点击后关闭菜单
            this.close(menuId);
        },

        /**
         * 全局点击监听
         */
        _setupGlobalClickListener: function() {
            var self = this;
            document.addEventListener('click', function(e) {
                // 找到点击的菜单或触发器
                var clickedMenu = e.target.closest('.smallmenu-dropdown');
                var clickedTrigger = e.target.closest('.smallmenu-trigger');

                if (clickedMenu || clickedTrigger) {
                    // 点击在菜单内或触发器上，不处理
                    return;
                }

                // 关闭所有开启 closeOnClickOutside 的菜单
                Object.keys(self._menus).forEach(function(menuId) {
                    var menuData = self._menus[menuId];
                    if (menuData && menuData.closeOnClickOutside) {
                        self.close(menuId);
                    }
                });
            });
        },

        /**
         * HTML转义
         */
        _escapeHtml: function(str) {
            if (typeof str !== 'string') return '';
            return str.replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }
    };

    // 导出
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = SmallMenu;
    } else {
        global.SmallMenu = SmallMenu;
    }

})(typeof window !== 'undefined' ? window : this);
