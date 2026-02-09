const test = require('node:test');
const assert = require('node:assert/strict');

global.window = globalThis;

const __store = new Map();
global.window.sessionStorage = {
    getItem: (k) => (__store.has(String(k)) ? __store.get(String(k)) : null),
    setItem: (k, v) => { __store.set(String(k), String(v)); },
    removeItem: (k) => { __store.delete(String(k)); }
};

global.escapeHtml = function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
};

const api = require('../static/js/system_monitor.js');

test('commitShortId returns first 8 chars', () => {
    assert.equal(api.commitShortId('0123456789abcdef'), '01234567');
    assert.equal(api.commitShortId('abc'), 'abc');
    assert.equal(api.commitShortId(null), '');
});

test('truncate adds ellipsis only when exceeding maxLen', () => {
    const a = api.truncate('hello', 60);
    assert.deepEqual(a, { text: 'hello', truncated: false });

    const long = 'a'.repeat(61);
    const b = api.truncate(long, 60);
    assert.equal(b.truncated, true);
    assert.equal(b.text.length, 61);
    assert.ok(b.text.endsWith('…'));
});

test('commitUrl encodes hash and repoPath into /commit/<hash>?repoPath=', () => {
    const url = api.commitUrl('C:\\repo path\\sub', 'abc123');
    assert.ok(url.startsWith('/commit/abc123?repoPath='));
    assert.ok(url.includes(encodeURIComponent('C:\\repo path\\sub')));
});

test('prepareCommitNavigation caches scroll and sets return flag', () => {
    __store.clear();
    const listEl = { scrollTop: 321 };
    const url = api.prepareCommitNavigation('C:\\repo', listEl, 'deadbeef');
    assert.ok(url.includes('/commit/deadbeef?repoPath='));
    assert.equal(global.window.sessionStorage.getItem(api.scrollKey('C:\\repo')), '321');
    const raw = global.window.sessionStorage.getItem('gitCommitReturn');
    assert.ok(raw);
    const parsed = JSON.parse(raw);
    assert.equal(parsed.repoPath, 'C:\\repo');
});

test('nextActiveIndex respects boundaries', () => {
    assert.equal(api.nextActiveIndex(-1, 'ArrowDown', 5), 1);
    assert.equal(api.nextActiveIndex(0, 'ArrowUp', 5), 0);
    assert.equal(api.nextActiveIndex(4, 'ArrowDown', 5), 4);
    assert.equal(api.nextActiveIndex(2, 'Other', 5), 2);
    assert.equal(api.nextActiveIndex(2, 'ArrowDown', 0), -1);
});

test('emptyHtml contains placeholder text', () => {
    const html = api.emptyHtml();
    assert.ok(html.includes('暂无提交记录'));
});

test('errorBannerHtml escapes message and contains retry button', () => {
    const html = api.errorBannerHtml('<b>x</b>&y');
    assert.ok(!html.includes('<b>'));
    assert.ok(html.includes('&lt;b&gt;x&lt;/b&gt;&amp;y'));
    assert.ok(html.includes('id="gitRetryBtn"'));
});

test('commitItemHtml renders escaped content and truncates subject to 60 chars', () => {
    const commit = {
        hash: '0123456789abcdef',
        author: '<img src=x onerror=alert(1)>',
        committed_at: '2026-01-01 12:34',
        subject: 'A'.repeat(80) + ' & <script>alert(1)</script>'
    };
    const html = api.commitItemHtml(commit, 'main', 'C:\\repo', 0);
    assert.ok(html.includes('01234567'));
    assert.ok(!html.includes('<img'));
    assert.ok(!html.includes('<script>'));
    assert.ok(html.includes('&lt;img'));
    assert.ok(html.includes('&lt;script&gt;'));
    assert.ok(html.includes('data-hash="0123456789abcdef"'));
    assert.ok(html.includes('data-index="0"'));
    assert.ok(html.includes('main'));
});

test('dirtyLineHtml renders push button only when hasChanges', () => {
    const dirty = api.dirtyLineHtml(true, '✗ Dirty', ' [+1]');
    assert.ok(dirty.includes('id="gitRepoDirtyLine"'));
    assert.ok(dirty.includes('id="gitDiffBtn"'));
    assert.ok(dirty.includes('id="gitPushBtn"'));
    assert.ok(dirty.includes('推送变更'));

    const clean = api.dirtyLineHtml(false, '✓ Clean', '');
    assert.ok(clean.includes('id="gitRepoDirtyLine"'));
    assert.ok(!clean.includes('id="gitDiffBtn"'));
    assert.ok(!clean.includes('id="gitPushBtn"'));
});
