const path = require('node:path');
const fs = require('node:fs');

module.exports = async () => {
    const pidFile = path.join(__dirname, '.server-pid');
    if (!fs.existsSync(pidFile)) return;
    const pid = Number(fs.readFileSync(pidFile, 'utf-8'));
    try { process.kill(pid); } catch (e) {}
    try { fs.rmSync(pidFile, { force: true }); } catch (e) {}
};

