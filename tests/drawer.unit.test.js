const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function createClassList(initial) {
    const set = new Set(initial || []);
    return {
        add: function(c) { set.add(c); },
        remove: function(c) { set.delete(c); },
        contains: function(c) { return set.has(c); },
        toArray: function() { return Array.from(set); }
    };
}

function createElement(id, classes) {
    const classList = createClassList(classes);
    const events = [];
    return {
        id,
        classList,
        _events: events,
        dispatchEvent: function(ev) { events.push(ev); return true; }
    };
}

function createDom(elementsById) {
    const listeners = {};
    const allEls = Object.values(elementsById);

    function matchesSelector(el, selector) {
        if (!selector) return false;
        const parts = selector.split('.').filter(Boolean);
        if (parts.length === 0) return false;
        return parts.every(function(p) { return el.classList.contains(p); });
    }

    return {
        elementsById,
        document: {
            getElementById: function(id) { return elementsById[id] || null; },
            querySelectorAll: function(selector) {
                const selectors = selector.split(',').map(function(s) { return s.trim(); }).filter(Boolean);
                return allEls.filter(function(el) { return selectors.some(function(sel) { return matchesSelector(el, sel); }); });
            },
            addEventListener: function(type, cb) { listeners[type] = cb; }
        },
        getListener: function(type) { return listeners[type]; }
    };
}

function loadGlobalsJs(context) {
    const file = path.join(__dirname, '..', 'static', 'js', 'globals.js');
    const code = fs.readFileSync(file, 'utf8');
    vm.runInContext(code, context);
}

test('Drawer open/close toggles classes and dispatches events', async () => {
    const elements = {
        searchModal: createElement('searchModal', ['drawer']),
        searchBackdrop: createElement('searchBackdrop', ['drawer-backdrop'])
    };
    const dom = createDom(elements);

    const sandbox = {
        window: {},
        document: dom.document,
        setTimeout,
        btoa: function() { return ''; },
        CustomEvent: class CustomEvent {
            constructor(type, init) {
                this.type = type;
                this.detail = init && init.detail;
            }
        }
    };
    vm.createContext(sandbox);
    loadGlobalsJs(sandbox);

    const Drawer = vm.runInContext('Drawer', sandbox);
    assert.equal(typeof Drawer, 'object');

    let opened = false;
    Drawer.open('searchModal', { onOpen: function() { opened = true; } });
    assert.equal(opened, true);
    assert.equal(elements.searchModal.classList.contains('open'), true);
    assert.equal(elements.searchBackdrop.classList.contains('open'), true);
    assert.equal(elements.searchModal._events.some(function(e) { return e.type === 'drawer:open'; }), true);

    let closed = false;
    let afterClosed = false;
    Drawer.close('searchModal', {
        onClose: function() { closed = true; },
        afterClose: function() { afterClosed = true; }
    });

    assert.equal(closed, true);
    assert.equal(elements.searchModal.classList.contains('open'), false);
    assert.equal(elements.searchBackdrop.classList.contains('open'), false);
    assert.equal(elements.searchModal._events.some(function(e) { return e.type === 'drawer:close'; }), true);

    await new Promise(function(r) { setTimeout(r, 320); });
    assert.equal(afterClosed, true);
    assert.equal(elements.searchModal._events.some(function(e) { return e.type === 'drawer:after-close'; }), true);
});

test('Escape closes all open drawers', async () => {
    const elements = {
        searchModal: createElement('searchModal', ['drawer']),
        searchBackdrop: createElement('searchBackdrop', ['drawer-backdrop']),
        trashDrawer: createElement('trashDrawer', ['drawer']),
        trashBackdrop: createElement('trashBackdrop', ['drawer-backdrop'])
    };
    const dom = createDom(elements);

    const sandbox = {
        window: {},
        document: dom.document,
        setTimeout,
        btoa: function() { return ''; },
        CustomEvent: class CustomEvent {
            constructor(type, init) {
                this.type = type;
                this.detail = init && init.detail;
            }
        }
    };
    vm.createContext(sandbox);
    loadGlobalsJs(sandbox);

    const Drawer = vm.runInContext('Drawer', sandbox);
    Drawer.open('searchModal');
    Drawer.open('trashDrawer');
    assert.equal(elements.searchModal.classList.contains('open'), true);
    assert.equal(elements.trashDrawer.classList.contains('open'), true);

    const onKeydown = dom.getListener('keydown');
    assert.equal(typeof onKeydown, 'function');
    onKeydown({ key: 'Escape' });

    assert.equal(elements.searchModal.classList.contains('open'), false);
    assert.equal(elements.trashDrawer.classList.contains('open'), false);

    await new Promise(function(r) { setTimeout(r, 320); });
    assert.equal(elements.searchModal._events.some(function(e) { return e.type === 'drawer:after-close'; }), true);
    assert.equal(elements.trashDrawer._events.some(function(e) { return e.type === 'drawer:after-close'; }), true);
});
