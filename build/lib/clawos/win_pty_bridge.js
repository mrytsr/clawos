const readline = require('node:readline');
const os = require('node:os');

let pty = null;
let ptyProcess = null;
let outBuf = '';
let outTimer = null;
const OUT_FLUSH_MS = 16;
const OUT_MAX_BUF = 64 * 1024;

function send(obj) {
  try {
    process.stdout.write(JSON.stringify(obj) + '\n');
  } catch (e) {
    try {
      process.stdout.write('{"type":"error","message":"bridge_send_failed"}\n');
    } catch (e2) {}
  }
}

function flushOut() {
  if (!outBuf) return;
  const payload = outBuf;
  outBuf = '';
  if (outTimer) {
    clearTimeout(outTimer);
    outTimer = null;
  }
  send({ type: 'output', data: payload });
}

function startPty(opts) {
  if (ptyProcess) return;
  const shell =
    (opts && typeof opts.shell === 'string' && opts.shell) ||
    (os.platform() === 'win32' ? 'powershell.exe' : 'bash');
  const args = (opts && Array.isArray(opts.args)) ? opts.args : [];
  const cwd = (opts && typeof opts.cwd === 'string' && opts.cwd) ? opts.cwd : process.cwd();
  const cols = (opts && Number.isFinite(opts.cols) && opts.cols > 0) ? opts.cols : 80;
  const rows = (opts && Number.isFinite(opts.rows) && opts.rows > 0) ? opts.rows : 24;
  const nextEnv = { ...process.env, TERM: 'xterm-256color', CHERE_INVOKING: '1' };
  if (!nextEnv.LANG) nextEnv.LANG = 'C.UTF-8';
  if (!nextEnv.LC_ALL) nextEnv.LC_ALL = 'C.UTF-8';
  if (!nextEnv.LC_CTYPE) nextEnv.LC_CTYPE = 'C.UTF-8';

  pty = require('node-pty');
  try {
    ptyProcess = pty.spawn(shell, args, {
      name: 'xterm-256color',
      cols,
      rows,
      cwd,
      env: nextEnv
    });
  } catch (e) {
    send({ type: 'output', data: '\r\n*** 启动终端失败: ' + String(e && e.message ? e.message : e) + ' ***\r\n' });
    process.exit(1);
  }

  ptyProcess.onData((data) => {
    if (!data) return;
    outBuf += data;
    if (outBuf.length >= OUT_MAX_BUF) {
      flushOut();
      return;
    }
    if (!outTimer) {
      outTimer = setTimeout(flushOut, OUT_FLUSH_MS);
    }
  });

  ptyProcess.onExit((ev) => {
    flushOut();
    send({ type: 'exit', exitCode: ev && ev.exitCode, signal: ev && ev.signal });
    process.exit(0);
  });
}

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
rl.on('line', (line) => {
  let msg = null;
  try {
    msg = JSON.parse(line);
  } catch (e) {
    return;
  }
  if (!msg || typeof msg.type !== 'string') return;

  if (msg.type === 'init') {
    startPty({
      shell: msg.shell,
      args: msg.args,
      cwd: msg.cwd,
      cols: msg.cols,
      rows: msg.rows
    });
    return;
  }
  if (!ptyProcess) return;

  if (msg.type === 'input') {
    const data = (msg && typeof msg.data === 'string') ? msg.data : '';
    if (data) ptyProcess.write(data);
    return;
  }
  if (msg.type === 'resize') {
    const cols = Number(msg.cols);
    const rows = Number(msg.rows);
    if (Number.isFinite(cols) && Number.isFinite(rows) && cols > 0 && rows > 0) {
      try {
        ptyProcess.resize(cols, rows);
      } catch (e) {}
    }
    return;
  }
  if (msg.type === 'close') {
    try {
      ptyProcess.kill();
    } catch (e) {}
    process.exit(0);
  }
});

rl.on('close', () => {
  if (ptyProcess) {
    try {
      ptyProcess.kill();
    } catch (e) {}
  }
  process.exit(0);
});
