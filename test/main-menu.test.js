const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

function readText(relPath) {
  return fs.readFileSync(path.join(__dirname, '..', relPath), 'utf8');
}

function extractWindowFunctionBody(src, fnName) {
  const re = new RegExp(
    `window\\.${fnName}\\s*=\\s*function\\([^)]*\\)\\s*\\{([\\s\\S]*?)\\n\\};`,
    'm',
  );
  const m = src.match(re);
  assert.ok(m, `missing window.${fnName} function`);
  return m[1];
}

test('开始菜单：保持打开且无障碍属性正确', () => {
  const src = readText('static/js/globals.js');

  const closeBody = extractWindowFunctionBody(src, 'closeMainMenuModal');
  assert.match(closeBody, /d\.setAttribute\('aria-hidden',\s*'true'\)/);
  assert.doesNotMatch(closeBody, /b\.setAttribute\('aria-hidden'/);

  const openBody = extractWindowFunctionBody(src, 'openMainMenuModal');
  assert.match(openBody, /d\.setAttribute\('aria-hidden',\s*'false'\)/);
  assert.doesNotMatch(openBody, /b\.setAttribute\('aria-hidden'/);
  assert.ok(
    openBody.includes('if (active && !d.contains(active) && active !== d) return;'),
    'missing focus-trap guard when focus is outside main menu',
  );

  const handleBody = extractWindowFunctionBody(src, 'handleMainMenu');
  assert.ok(
    !handleBody.includes('closeMainMenuModal'),
    'handleMainMenu should not close the main menu automatically',
  );
});
