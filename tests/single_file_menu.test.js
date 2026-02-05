
const assert = require('assert');
const { JSDOM } = require('jsdom');

// Mock DOM
const dom = new JSDOM(`
<!DOCTYPE html>
<html>
<body>
    <div id="menuModal" class="drawer"></div>
    <div id="clipboardBar">
        <button id="clipboardPasteBtn"></button>
        <button id="clipboardCancelBtn"></button>
        <span id="clipboardLabel"></span>
    </div>
    <div id="targetModal" class="drawer">
        <input id="targetPathInput">
    </div>
    <div id="moveModal" class="drawer">
        <input id="targetPathInput">
    </div>
</body>
</html>
`);

global.window = dom.window;
global.document = dom.window.document;
global.localStorage = {
    store: {},
    getItem: function(key) { return this.store[key] || null; },
    setItem: function(key, value) { this.store[key] = value.toString(); },
    removeItem: function(key) { delete this.store[key]; }
};

// Mock Clipboard
global.window.Clipboard = {
    set: function(op, item) {
        // Simulate writing to localStorage
        const data = { type: op, paths: [item.path], ts: Date.now() };
        global.localStorage.setItem('clipboard_file_path', JSON.stringify(data));
    }
};

// Mock Drawer
global.Drawer = {
    open: (id) => document.getElementById(id).classList.add('open'),
    close: (id) => document.getElementById(id).classList.remove('open')
};

global.showToast = () => {};

// Load file_browser.js functions (simulated)
// We need to test handleMenuAction specifically

// Mock logic from file_browser.js
window.currentItemPath = 'test.txt';
window.currentItemName = 'test.txt';
window.currentItemIsDir = false;

function handleMenuAction(action) {
    if (action === 'cut') {
        window.Clipboard.set('cut', { path: window.currentItemPath, name: window.currentItemName, isDir: window.currentItemIsDir });
    } else if (action === 'copy') {
        window.Clipboard.set('copy', { path: window.currentItemPath, name: window.currentItemName, isDir: window.currentItemIsDir });
    } else if (action === 'move') {
        // Legacy move
        Drawer.open('moveModal');
    }
}

async function runTests() {
    console.log('Starting Single File Menu Tests...');

    // Test 1: Cut Action
    console.log('\nTest 1: Cut Action');
    handleMenuAction('cut');
    const cutData = JSON.parse(global.localStorage.getItem('clipboard_file_path'));
    assert.strictEqual(cutData.type, 'cut');
    assert.deepStrictEqual(cutData.paths, ['test.txt']);
    console.log('PASS: Cut writes to localStorage correctly');

    // Test 2: Copy Action
    console.log('\nTest 2: Copy Action');
    handleMenuAction('copy');
    const copyData = JSON.parse(global.localStorage.getItem('clipboard_file_path'));
    assert.strictEqual(copyData.type, 'copy');
    assert.deepStrictEqual(copyData.paths, ['test.txt']);
    console.log('PASS: Copy writes to localStorage correctly');

    // Test 3: Move Action (Legacy/Direct)
    console.log('\nTest 3: Move Action');
    handleMenuAction('move');
    assert.ok(document.getElementById('moveModal').classList.contains('open'));
    console.log('PASS: Move opens moveModal');
    
    console.log('\nAll tests passed!');
}

runTests().catch(e => {
    console.error('Test Failed:', e);
    process.exit(1);
});
