const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const fs = require('fs');

// Mock browser environment
global.window = {
    localStorage: {
        _data: {},
        getItem(k) { return this._data[k] || null; },
        setItem(k, v) { this._data[k] = String(v); },
        removeItem(k) { delete this._data[k]; },
        clear() { this._data = {}; }
    },
    showToast: () => {},
    refreshFileList: () => {}
};
global.document = {
    getElementById: () => null,
    createElement: () => ({ classList: { add:()=>{}, remove:()=>{} }, setAttribute:()=>{} }),
    body: { appendChild: () => {} },
    readyState: 'complete',
    addEventListener: () => {}
};
global.fetch = () => Promise.resolve({ json: () => ({ success: true }) });

// Load the module
// Since clipboard.js is a UMD module that assigns to root.Clipboard or module.exports
// We need to handle how it exports.
// Based on the file content:
// if (typeof module !== 'undefined' && module.exports) { module.exports = factory(); }
const Clipboard = require('../static/js/clipboard.js');

test('write saves state to localStorage', () => {
    global.window.localStorage.clear();
    const success = Clipboard.write('copy', 'foo.txt');
    assert.equal(success, true);
    
    const raw = global.window.localStorage.getItem('clipboard_file_path');
    assert.ok(raw);
    const data = JSON.parse(raw);
    assert.equal(data.type, 'copy');
    assert.equal(data.path, 'foo.txt');
    assert.equal(data.name, 'foo.txt');
    assert.ok(data.ts);
});

test('read retrieves state from localStorage', () => {
    global.window.localStorage.clear();
    const stateStr = JSON.stringify({
        type: 'cut',
        path: 'dir/bar.png',
        name: 'bar.png',
        ts: 123456
    });
    global.window.localStorage.setItem('clipboard_file_path', stateStr);
    
    const state = Clipboard.read();
    assert.deepEqual(state, {
        op: 'cut',
        path: 'dir/bar.png',
        name: 'bar.png',
        isDir: false,
        ts: 123456
    });
});

test('clear removes state', () => {
    global.window.localStorage.setItem('clipboard_file_path', 'something');
    Clipboard.clear();
    assert.equal(global.window.localStorage.getItem('clipboard_file_path'), null);
});

test('pasteHere calls fetch with correct parameters', async () => {
    let fetchCalled = false;
    let fetchUrl = '';
    let fetchBody = {};
    
    global.fetch = (url, opts) => {
        fetchCalled = true;
        fetchUrl = url;
        fetchBody = JSON.parse(opts.body);
        return Promise.resolve({ json: () => Promise.resolve({ success: true }) });
    };
    
    // Mock currentBrowsePath input
    global.document.getElementById = (id) => {
        if (id === 'currentBrowsePath') return { value: 'target/dir' };
        return null;
    };
    
    // Setup state
    Clipboard.write('copy', 'source.txt');
    
    await Clipboard.pasteHere();
    
    assert.equal(fetchCalled, true);
    assert.equal(fetchUrl, '/api/batch/copy');
    assert.deepEqual(fetchBody, {
        paths: ['source.txt'],
        target: 'target/dir'
    });
});

test('pasteHere (cut) calls move endpoint', async () => {
    let fetchUrl = '';
    global.fetch = (url, opts) => {
        fetchUrl = url;
        return Promise.resolve({ json: () => Promise.resolve({ success: true }) });
    };
    
    Clipboard.write('cut', 'source.txt');
    await Clipboard.pasteHere();
    
    assert.equal(fetchUrl, '/api/batch/move');
});
