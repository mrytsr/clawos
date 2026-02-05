const path = require('node:path');

module.exports = {
    testDir: path.join(__dirname, 'tests', 'e2e'),
    timeout: 60_000,
    retries: 0,
    use: {
        baseURL: 'http://127.0.0.1:6010',
        headless: true
    },
    globalSetup: path.join(__dirname, 'tests', 'e2e', 'global-setup.js'),
    globalTeardown: path.join(__dirname, 'tests', 'e2e', 'global-teardown.js')
};

