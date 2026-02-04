const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const { spawn } = require('node:child_process');

const { chromium } = require('playwright');
const pixelmatch = require('pixelmatch');
const { PNG } = require('pngjs');

function httpGetJson(url) {
    return new Promise((resolve, reject) => {
        const req = http.get(url, (res) => {
            let body = '';
            res.setEncoding('utf8');
            res.on('data', (chunk) => { body += chunk; });
            res.on('end', () => {
                try {
                    resolve(JSON.parse(body));
                } catch (e) {
                    reject(e);
                }
            });
        });
        req.on('error', reject);
        req.setTimeout(5000, () => {
            req.destroy(new Error('timeout'));
        });
    });
}

async function waitForServer(baseUrl, timeoutMs) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
        try {
            const data = await httpGetJson(baseUrl + '/api/test_socket');
            if (data && data.success) return;
        } catch (e) {
            await new Promise((r) => setTimeout(r, 200));
        }
    }
    throw new Error('server not ready: ' + baseUrl);
}

function startServer(port) {
    const env = Object.assign({}, process.env, {
        SERVER_HOST: '127.0.0.1',
        SERVER_PORT: String(port),
        SERVER_DEBUG: '0',
        SERVER_USE_RELOADER: '0'
    });
    const proc = spawn('python', ['app.py'], {
        env,
        stdio: ['ignore', 'pipe', 'pipe']
    });
    return proc;
}

async function stopServer(proc) {
    if (!proc || proc.killed) return;
    proc.kill('SIGTERM');
    await new Promise((r) => setTimeout(r, 200));
    if (!proc.killed) proc.kill('SIGKILL');
}

async function screenshotDrawerChrome(page, drawerId, normalizeHeader) {
    await page.evaluate((id, normalize) => {
        const m = document.getElementById(id);
        if (!m) throw new Error('missing drawer: ' + id);
        m.style.transition = 'none';
        m.style.height = '140px';
        m.style.maxHeight = '140px';
        m.style.overflow = 'hidden';
        const content = m.querySelector('.drawer-content');
        if (content) content.style.display = 'none';
        if (normalize) {
            const header = m.querySelector('.drawer-header');
            if (header) header.innerHTML = '<div class="drawer-title">TEST</div>';
        }
        if (typeof Drawer !== 'undefined' && Drawer && typeof Drawer.open === 'function') Drawer.open(id);
        const bId = id.replace('Modal', 'Backdrop').replace('Drawer', 'Backdrop');
        const b = document.getElementById(bId);
        if (b) b.style.transition = 'none';
    }, drawerId, normalizeHeader);
    await page.waitForTimeout(50);
    const buf = await page.locator('#' + drawerId).screenshot();
    await page.evaluate((id) => {
        if (typeof Drawer !== 'undefined' && Drawer && typeof Drawer.close === 'function') Drawer.close(id);
    }, drawerId);
    await page.waitForTimeout(50);
    return PNG.sync.read(buf);
}

test('search/trash drawer matches process drawer chrome and behaviors', async () => {
    const port = 6100 + Math.floor(Math.random() * 200);
    const baseUrl = 'http://127.0.0.1:' + port;
    const server = startServer(port);
    try {
        await waitForServer(baseUrl, 15000);

        const browser = await chromium.launch();
        try {
            const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
            await page.goto(baseUrl + '/', { waitUntil: 'networkidle' });

            const backdropColor = await page.evaluate(() => {
                const b = document.querySelector('.drawer-backdrop');
                if (!b) return null;
                return getComputedStyle(b).backgroundColor;
            });
            assert.equal(backdropColor, 'rgba(0, 0, 0, 0.45)');

            const searchPng = await screenshotDrawerChrome(page, 'searchModal', true);
            const processPng = await screenshotDrawerChrome(page, 'processModal', true);

            assert.equal(searchPng.width, processPng.width);
            assert.equal(searchPng.height, processPng.height);

            const diff = new PNG({ width: searchPng.width, height: searchPng.height });
            const numDiff = pixelmatch(
                searchPng.data,
                processPng.data,
                diff.data,
                searchPng.width,
                searchPng.height,
                { threshold: 0.1 }
            );
            const ratio = numDiff / (searchPng.width * searchPng.height);
            assert.ok(ratio < 0.001);

            const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
            await mobile.goto(baseUrl + '/', { waitUntil: 'networkidle' });
            const mobileOk = await mobile.evaluate(() => {
                const ids = ['searchModal', 'trashDrawer'];
                return ids.every((id) => {
                    const m = document.getElementById(id);
                    if (!m) return false;
                    const s = getComputedStyle(m);
                    return s.top === '0px' && s.bottom === '0px' && s.borderTopLeftRadius === '0px';
                });
            });
            assert.equal(mobileOk, true);
            await mobile.close();
            await page.close();
        } finally {
            await browser.close();
        }
    } finally {
        await stopServer(server);
    }
});
