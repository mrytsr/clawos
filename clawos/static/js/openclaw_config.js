(() => {
    function ensureSystemMonitorLoaded(cb) {
        if (typeof window.loadOpenclawConfig === 'function') {
            cb();
            return;
        }
        const script = document.createElement('script');
        script.src = '/static/js/system_monitor.js';
        script.onload = cb;
        document.head.appendChild(script);
    }

    function boot() {
        try {
            if (typeof window.switchBotTab === 'function') window.switchBotTab('config');
            if (typeof window.loadOpenclawConfig === 'function') window.loadOpenclawConfig();
            if (typeof window.loadBotHistory === 'function') window.loadBotHistory();
            if (typeof window.loadBotStats === 'function') window.loadBotStats();
        } catch (e) {}
    }

    function loadSystemMonitorThenBoot() {
        ensureSystemMonitorLoaded(boot);
    }

    const openclawEditModelFallback = function(provider, modelId) {
        ensureSystemMonitorLoaded(function() {
            if (window.openOpenclawEditModelModal && window.openOpenclawEditModelModal !== openclawEditModelFallback) {
                window.openOpenclawEditModelModal(provider, modelId);
            }
        });
    };
    if (typeof window.openOpenclawEditModelModal !== 'function') window.openOpenclawEditModelModal = openclawEditModelFallback;

    const openclawAddModelFallback = function() {
        ensureSystemMonitorLoaded(function() {
            if (window.openOpenclawAddModelModal && window.openOpenclawAddModelModal !== openclawAddModelFallback) {
                window.openOpenclawAddModelModal();
            }
        });
    };
    if (typeof window.openOpenclawAddModelModal !== 'function') window.openOpenclawAddModelModal = openclawAddModelFallback;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadSystemMonitorThenBoot);
    } else {
        loadSystemMonitorThenBoot();
    }
})();
