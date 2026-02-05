const path = require('node:path');
const fs = require('node:fs');
const http = require('node:http');
const { spawn } = require('node:child_process');

function requestOk(url) {
    return new Promise((resolve) => {
        const req = http.get(url, (res) => {
            res.resume();
            resolve(res.statusCode && res.statusCode >= 200 && res.statusCode < 500);
        });
        req.on('error', () => resolve(false));
        req.setTimeout(500, () => {
            req.destroy();
            resolve(false);
        });
    });
}

module.exports = async () => {
    const repoRoot = path.join(__dirname, '..', '..');
    const workspaceDir = path.join(__dirname, 'workspace');
    fs.rmSync(workspaceDir, { recursive: true, force: true });
    fs.mkdirSync(workspaceDir, { recursive: true });
    fs.mkdirSync(path.join(workspaceDir, 'dst'), { recursive: true });
    fs.writeFileSync(path.join(workspaceDir, 'abc.txt'), 'abc', 'utf-8');

    const env = Object.assign({}, process.env, {
        ROOT_DIR: workspaceDir,
        SERVER_PORT: '6010',
        SERVER_DEBUG: '0',
        SERVER_USE_RELOADER: '0'
    });

    const child = spawn('python', ['app.py'], {
        cwd: repoRoot,
        env,
        stdio: 'ignore',
        windowsHide: true
    });

    const pidFile = path.join(__dirname, '.server-pid');
    fs.writeFileSync(pidFile, String(child.pid), 'utf-8');

    const base = 'http://127.0.0.1:6010/';
    const deadline = Date.now() + 30_000;
    while (Date.now() < deadline) {
        const ok = await requestOk(base);
        if (ok) return;
        await new Promise((r) => setTimeout(r, 300));
    }
    try { process.kill(child.pid); } catch (e) {}
    throw new Error('server did not start');
};

