// ESLint Configuration for 6002_clawos
// Flat config format (ESLint 9.x)

export default [
    {
        ignores: ["node_modules/", "static/lib/"]
    },
    {
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: "script",
            globals: {
                // Browser globals
                window: "readonly",
                document: "readonly",
                navigator: "readonly",
                localStorage: "readonly",
                fetch: "readonly",
                setTimeout: "readonly",
                clearTimeout: "readonly",
                alert: "readonly",
                confirm: "readonly",
                prompt: "readonly",
                FormData: "readonly",
                btoa: "readonly",
                // Socket.IO
                io: "readonly",
                socketio: "readonly",
                // xterm.js
                Terminal: "readonly",
                FitAddon: "readonly",
                // Common UI functions (used across modules)
                showToast: "readonly",
                escapeHtml: "readonly",
                formatSize: "readonly",
                showUploadStatus: "readonly",
                openTerminal: "readonly",
                openPreview: "readonly",
                loadBotHistory: "readonly",
                botConnect: "readonly",
                botIsConnected: "writable",
                loadSystemdList: "readonly",
                // File browser globals
                currentItemPath: "writable",
                currentItemName: "writable",
                currentItemIsDir: "writable",
                // Drag globals
                isDragging: "writable",
                startY: "writable",
                startHeight: "writable",
                onDrag: "readonly",
                endDrag: "readonly",
                // Functions defined in other modules
                closeMenuModal: "readonly",
                closePreviewModal: "readonly",
                closeRenameModal: "readonly",
                closeDetailsModal: "readonly",
                doSearch: "readonly",
                refreshFileList: "readonly",
                showDetails: "readonly"
            }
        },
        rules: {
            "no-undef": "error",
            "no-redeclare": "off",
            "eqeqeq": ["error", "always"],
            "no-extra-semi": "warn",
            "semi": ["error", "always"]
        }
    }
];
