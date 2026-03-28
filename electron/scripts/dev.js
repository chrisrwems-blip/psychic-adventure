/**
 * Dev orchestrator for Electron.
 * Starts: Python backend (uvicorn --reload) + Vite dev server + Electron window.
 * Waits for both servers to be ready before launching Electron.
 */
const { spawn } = require('child_process');
const treeKill = require('tree-kill');
const { BACKEND_DIR, FRONTEND_DIR, ELECTRON_DIR } = require('../lib/constants');

const isWindows = process.platform === 'win32';
const pythonCmd = isWindows ? 'python' : 'python3';
const npmCmd = isWindows ? 'npm.cmd' : 'npm';

const children = [];

function spawnTracked(cmd, args, opts) {
  const child = spawn(cmd, args, {
    stdio: 'inherit',
    shell: isWindows,
    ...opts,
  });
  children.push(child);
  child.on('error', (err) => {
    console.error(`[dev] Failed to start ${cmd}:`, err.message);
  });
  return child;
}

function cleanup() {
  console.log('\n[dev] Shutting down...');
  children.forEach((child) => {
    if (child.pid && !child.killed) {
      treeKill(child.pid, 'SIGTERM', () => {});
    }
  });
  setTimeout(() => process.exit(0), 2000);
}

process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);

// 1. Start Python backend with hot reload
console.log('[dev] Starting Python backend...');
spawnTracked(pythonCmd, [
  '-m', 'uvicorn', 'app.main:app',
  '--host', '127.0.0.1',
  '--port', '8000',
  '--reload',
], { cwd: BACKEND_DIR });

// 2. Start Vite dev server
console.log('[dev] Starting Vite dev server...');
spawnTracked(npmCmd, ['run', 'dev'], { cwd: FRONTEND_DIR });

// 3. Wait for both servers, then launch Electron
const waitOn = require('wait-on');

waitOn({
  resources: [
    'http-get://localhost:8000/api/health',
    'http-get://localhost:5173',
  ],
  timeout: 30000,
  interval: 1000,
})
  .then(() => {
    console.log('[dev] Both servers ready. Starting Electron...');
    const electronPath = require('electron');
    const electron = spawnTracked(String(electronPath), ['.'], {
      cwd: ELECTRON_DIR,
      shell: false,
      env: { ...process.env, ELECTRON_IS_DEV: '1' },
    });
    electron.on('exit', cleanup);
  })
  .catch((err) => {
    console.error('[dev] Servers failed to start within 30s:', err.message);
    cleanup();
  });
