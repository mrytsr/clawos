const test = require('node:test');
const assert = require('node:assert/strict');

const Clipboard = require('../static/js/clipboard.js');

function createMemoryStorage() {
    const store = new Map();
    return {
        getItem: (k) => (store.has(k) ? store.get(k) : null),
        setItem: (k, v) => { store.set(k, String(v)); },
        removeItem: (k) => { store.delete(k); },
        _store: store
    };
}

test('createState normalizes inputs', () => {
    const st = Clipboard.createState('copy', { path: 'a/b.txt', name: 'b.txt', isDir: false });
    assert.equal(st.op, 'copy');
    assert.equal(st.path, 'a/b.txt');
    assert.equal(st.name, 'b.txt');
    assert.equal(st.isDir, false);
    assert.equal(typeof st.ts, 'number');
});

test('write/read/clear roundtrip', () => {
    const storage = createMemoryStorage();
    const state = Clipboard.createState('cut', { path: 'x', name: 'x', isDir: true });
    assert.equal(Clipboard.write(storage, state), true);
    const loaded = Clipboard.read(storage);
    assert.deepEqual(
        { op: loaded.op, path: loaded.path, name: loaded.name, isDir: loaded.isDir },
        { op: 'cut', path: 'x', name: 'x', isDir: true }
    );
    assert.equal(Clipboard.clear(storage), true);
    assert.equal(Clipboard.read(storage), null);
});

test('read ignores invalid JSON', () => {
    const storage = createMemoryStorage();
    storage.setItem(Clipboard.STORAGE_KEY, '{bad json');
    assert.equal(Clipboard.read(storage), null);
});

test('buildPasteRequest chooses endpoint', () => {
    const cutReq = Clipboard.buildPasteRequest({ op: 'cut', path: 'a', name: 'a', isDir: false }, 'dst');
    assert.equal(cutReq.endpoint, '/api/batch/move');
    assert.deepEqual(cutReq.payload, { paths: ['a'], target: 'dst' });

    const copyReq = Clipboard.buildPasteRequest({ op: 'copy', path: 'b', name: 'b', isDir: false }, '');
    assert.equal(copyReq.endpoint, '/api/batch/copy');
    assert.deepEqual(copyReq.payload, { paths: ['b'], target: '' });
});

test('paste returns ok on api success', async () => {
    const fakeFetch = (url, init) => {
        assert.equal(url, '/api/batch/copy');
        const body = JSON.parse(init.body);
        assert.deepEqual(body, { paths: ['a/b.txt'], target: '' });
        return Promise.resolve({
            json: () => Promise.resolve({ success: true, data: { message: 'ok' } })
        });
    };
    const res = await Clipboard.paste({ op: 'copy', path: 'a/b.txt', name: 'b.txt' }, '', fakeFetch);
    assert.equal(res.ok, true);
});

test('paste returns error on fetch rejection', async () => {
    const fakeFetch = () => Promise.reject(new Error('net'));
    const res = await Clipboard.paste({ op: 'cut', path: 'a', name: 'a' }, 'dst', fakeFetch);
    assert.equal(res.ok, false);
    assert.equal(res.error, 'net');
});
