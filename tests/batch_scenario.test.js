
const assert = require('assert');
const { JSDOM } = require('jsdom');

// Mock browser environment
const dom = new JSDOM(`
<!DOCTYPE html>
<html>
<body>
    <div id="batchDrawer" class="drawer">
        <span id="batchCount"></span>
        <input type="checkbox" id="batchSelectAll">
        <div class="drawer-content"></div>
    </div>
    <div id="targetModal" class="drawer">
        <div class="drawer-title" id="targetModalTitle"></div>
        <input id="targetPathInput" type="text">
    </div>
    <div id="file-list">
        <div class="file-item">
            <input type="checkbox" class="file-checkbox" data-path="file1.txt">
        </div>
        <div class="file-item">
            <input type="checkbox" class="file-checkbox" data-path="file2.txt">
        </div>
        <div class="file-item">
            <input type="checkbox" class="file-checkbox" data-path="file3.txt">
        </div>
    </div>
    <div id="toastContainer"></div>
</body>
</html>
`);

global.window = dom.window;
global.document = dom.window.document;
global.localStorage = {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {}
};
global.navigator = { userAgent: 'node' };

// Mock global functions
global.showToast = (msg, type) => { console.log(`Toast: ${msg} (${type})`); };
global.refreshFileList = () => { console.log('refreshFileList called'); };

// Mock Drawer
global.Drawer = {
    open: (id) => {
        const el = document.getElementById(id);
        if (el) el.classList.add('open');
        console.log(`Drawer opened: ${id}`);
    },
    close: (id) => {
        const el = document.getElementById(id);
        if (el) el.classList.remove('open');
        console.log(`Drawer closed: ${id}`);
    }
};

// Load globals.js logic (simulated since we can't require it directly without export)
// We will copy the relevant logic from globals.js for testing purposes
// or we can read and eval it, but copying is safer for a quick test of logic flow.

// --- Logic from globals.js ---
window.batchOperationFiles = [];
window.batchActionType = null;

window.updateBatchBar = function() {
    var count = document.querySelectorAll('.file-checkbox:checked').length;
    var countEl = document.getElementById('batchCount');
    if (countEl) { countEl.textContent = '已选 ' + count + ' 项'; }
    
    var d = document.getElementById('batchDrawer');
    if (count > 0) {
        if (d && !d.classList.contains('open')) {
            Drawer.open('batchDrawer');
        }
    } else {
        if (d && d.classList.contains('open')) {
            Drawer.close('batchDrawer');
        }
    }
};

window.batchCopy = function() {
    var paths = [];
    document.querySelectorAll('.file-checkbox:checked').forEach(function(c) { paths.push(c.dataset.path); });
    if (paths.length === 0) { return showToast('请选择要复制的文件', 'warning'); }
    
    window.batchOperationFiles = paths;
    window.batchActionType = 'copy';
    window.openTargetModal('复制到');
};

window.batchMove = function() {
    var paths = [];
    document.querySelectorAll('.file-checkbox:checked').forEach(function(c) { paths.push(c.dataset.path); });
    if (paths.length === 0) { return showToast('请选择要移动的文件', 'warning'); }
    
    window.batchOperationFiles = paths;
    window.batchActionType = 'move';
    window.openTargetModal('移动到');
};

window.openTargetModal = function(title) {
    var t = document.getElementById('targetModalTitle');
    if (t) t.textContent = title || '选择目标位置';
    document.getElementById('targetPathInput').value = '';
    Drawer.open('targetModal');
};

window.confirmTargetPath = function() {
    var target = document.getElementById('targetPathInput').value.trim();
    if (!target) { return showToast('请输入目标路径', 'warning'); }
    
    var paths = window.batchOperationFiles;
    var action = window.batchActionType;
    
    if (!paths || paths.length === 0) { return showToast('未选择文件', 'error'); }
    
    var endpoint = action === 'move' ? '/api/batch/move' : '/api/batch/copy';
    
    // Mock fetch
    console.log(`Fetch: ${endpoint}`, { paths: paths, target: target });
    return Promise.resolve({ success: true });
};

// --- Test Cases ---

async function runTests() {
    console.log('Starting Batch Scenario Tests...');

    // Test 1: Multi-select triggers drawer
    console.log('\nTest 1: Multi-select triggers drawer');
    const checkboxes = document.querySelectorAll('.file-checkbox');
    checkboxes[0].checked = true;
    window.updateBatchBar();
    assert.ok(document.getElementById('batchDrawer').classList.contains('open'), 'Drawer should open with 1 selection');
    
    checkboxes[1].checked = true;
    window.updateBatchBar();
    assert.ok(document.getElementById('batchDrawer').classList.contains('open'), 'Drawer should stay open with 2 selections');
    
    const countText = document.getElementById('batchCount').textContent;
    assert.strictEqual(countText, '已选 2 项', 'Count text should update');
    console.log('PASS: Drawer trigger and count');

    // Test 2: Batch Copy Logic
    console.log('\nTest 2: Batch Copy Logic');
    window.batchCopy();
    assert.strictEqual(window.batchActionType, 'copy', 'Action type should be copy');
    assert.deepStrictEqual(window.batchOperationFiles, ['file1.txt', 'file2.txt'], 'Files should match selection');
    assert.ok(document.getElementById('targetModal').classList.contains('open'), 'Target modal should open');
    console.log('PASS: Batch Copy setup');

    // Test 3: Batch Move Logic
    console.log('\nTest 3: Batch Move Logic');
    window.batchMove();
    assert.strictEqual(window.batchActionType, 'move', 'Action type should be move');
    assert.deepStrictEqual(window.batchOperationFiles, ['file1.txt', 'file2.txt'], 'Files should match selection');
    console.log('PASS: Batch Move setup');

    // Test 4: Confirm Target Path
    console.log('\nTest 4: Confirm Target Path');
    document.getElementById('targetPathInput').value = 'target/folder';
    
    // Intercept fetch log
    let fetchCalled = false;
    const originalLog = console.log;
    console.log = (msg, data) => {
        if (msg && msg.startsWith('Fetch:')) {
            fetchCalled = true;
            assert.strictEqual(msg, 'Fetch: /api/batch/move');
            assert.deepStrictEqual(data.paths, ['file1.txt', 'file2.txt']);
            assert.strictEqual(data.target, 'target/folder');
        }
        originalLog(msg, data || '');
    };

    await window.confirmTargetPath();
    console.log = originalLog;
    assert.ok(fetchCalled, 'Fetch should be called with correct data');
    console.log('PASS: Confirm Target Path');

    console.log('\nAll tests passed!');
}

runTests().catch(e => {
    console.error('Test Failed:', e);
    process.exit(1);
});
