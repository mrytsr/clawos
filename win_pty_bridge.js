const readline = require('node:readline');
const os = require('node:os');

let pty = null;
let ptyProcess = null;

function send(obj) {
  try {
    process.stdout.write(JSON.stringify(obj) + '\n');
  } catch (e) {
    try {
      process.stdout.write('{"type":"error","message":"bridge_send_failed"}\n');
    } catch (e2) {}
  }
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

  pty = require('node-pty');
  ptyProcess = pty.spawn(shell, args, {
    name: 'xterm-256color',
    cols,
    rows,
    cwd,
    env: process.env
  });

  ptyProcess.onData((data) => {
    send({ type: 'output', data: data });
  });

  ptyProcess.onExit((ev) => {
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
