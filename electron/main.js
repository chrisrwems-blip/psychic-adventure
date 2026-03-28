const { app, BrowserWindow, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');
const treeKill = require('tree-kill');

const isDev = !app.isPackaged;
const BACKEND_PORT = 8000;
const VITE_PORT = 5173;

let mainWindow = null;
let backendProcess = null;

// Single instance lock — prevent multiple windows
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
}

function getBackendExecutable() {
  if (isDev) return null; // dev.js starts backend separately
  const name = process.platform === 'win32'
    ? 'DC_Submittal_Review_Backend.exe'
    : 'DC_Submittal_Review_Backend';
  return path.join(process.resourcesPath, 'backend', name);
}

function startBackend() {
  const exe = getBackendExecutable();
  if (!exe) return; // dev mode — backend started by dev.js

  backendProcess = spawn(exe, [], {
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
    cwd: app.getPath('userData'),
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`[backend] ${data.toString().trim()}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[backend] ${data.toString().trim()}`);
  });

  backendProcess.on('exit', (code) => {
    console.log(`Backend exited with code ${code}`);
    backendProcess = null;
  });
}

function waitForBackend(maxRetries = 30, intervalMs = 1000) {
  return new Promise((resolve, reject) => {
    let attempts = 0;

    const poll = () => {
      attempts++;
      const req = http.get(
        `http://localhost:${BACKEND_PORT}/api/health`,
        (res) => {
          if (res.statusCode === 200) {
            resolve();
          } else {
            retry();
          }
        }
      );
      req.on('error', retry);
      req.setTimeout(2000, () => {
        req.destroy();
        retry();
      });
    };

    const retry = () => {
      if (attempts < maxRetries) {
        setTimeout(poll, intervalMs);
      } else {
        reject(new Error(`Backend did not respond after ${maxRetries} attempts`));
      }
    };

    poll();
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    title: 'DC Submittal Review',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  // Dev: load from Vite dev server. Prod: load from backend (serves static files).
  const url = isDev
    ? `http://localhost:${VITE_PORT}`
    : `http://localhost:${BACKEND_PORT}`;

  mainWindow.loadURL(url);

  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function killBackend() {
  if (!backendProcess) return;
  const pid = backendProcess.pid;
  backendProcess = null;

  treeKill(pid, 'SIGTERM', (err) => {
    if (err) console.error('Failed to kill backend process tree:', err);
  });
}

// --- App lifecycle ---

app.on('ready', async () => {
  startBackend();

  try {
    await waitForBackend();
  } catch (err) {
    dialog.showErrorBox(
      'Startup Error',
      'The backend server failed to start. Please check the logs and try again.'
    );
    app.quit();
    return;
  }

  createWindow();
});

app.on('window-all-closed', () => {
  killBackend();
  app.quit();
});

app.on('before-quit', killBackend);

app.on('second-instance', () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  }
});
