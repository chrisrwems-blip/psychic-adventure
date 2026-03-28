/**
 * Production build script for Electron.
 *
 * 1. Builds frontend (npm run build)
 * 2. Copies built frontend to backend/static/
 * 3. Generates backend/app/production.py (serves static files + API)
 * 4. Generates backend/electron_launcher.py (uvicorn entry, no browser)
 * 5. Runs PyInstaller --onedir to create backend sidecar
 * 6. Moves output to dist/backend/
 *
 * Run from: electron/ directory
 * Prerequisite: pip install pyinstaller
 */
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const { ROOT, BACKEND_DIR: BACKEND, FRONTEND_DIR: FRONTEND } = require('../lib/constants');

const DIST_BACKEND = path.join(ROOT, 'dist', 'backend');

const isWindows = process.platform === 'win32';
const sep = isWindows ? ';' : ':';

function step(msg) {
  console.log(`\n${'='.repeat(60)}\n  ${msg}\n${'='.repeat(60)}\n`);
}

function run(cmd, opts) {
  execSync(cmd, { stdio: 'inherit', shell: true, ...opts });
}

// Step 1: Build frontend
step('Building frontend');
run('npm install', { cwd: FRONTEND });
run('npm run build', { cwd: FRONTEND });

const staticDir = path.join(BACKEND, 'static');
fs.rmSync(staticDir, { recursive: true, force: true });
fs.cpSync(path.join(FRONTEND, 'dist'), staticDir, { recursive: true });
console.log(`  Frontend copied to ${staticDir}`);

// Step 2: Generate production.py
step('Generating production.py');
const productionPy = `"""Production app — serves both API and frontend from a single process."""
import os
from app.main import app
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        file_path = os.path.join(STATIC_DIR, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
`;
fs.writeFileSync(path.join(BACKEND, 'app', 'production.py'), productionPy);

// Step 3: Generate electron_launcher.py (no browser, just the server)
step('Generating electron_launcher.py');
const launcherPy = `"""Sidecar backend for Electron — starts the server without opening a browser."""
import os
import sys

if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

import uvicorn
from app.production import app

uvicorn.run(app, host="127.0.0.1", port=8000)
`;
fs.writeFileSync(path.join(BACKEND, 'electron_launcher.py'), launcherPy);

// Step 4: Run PyInstaller --onedir
step('Running PyInstaller (onedir mode)');
const hiddenImports = [
  'uvicorn.logging',
  'uvicorn.protocols.http',
  'uvicorn.protocols.http.auto',
  'uvicorn.protocols.http.h11_impl',
  'uvicorn.lifespan',
  'uvicorn.lifespan.on',
  'app.main',
  'app.production',
  'app.database',
  'app.routers.projects',
  'app.routers.submittals',
  'app.routers.reviews',
  'app.routers.comments',
  'app.routers.emails',
  'app.routers.register',
  'app.routers.rfis',
  'app.routers.feedback',
  'sqlalchemy.dialects.sqlite',
  'aiofiles',
  'multipart',
].map((m) => `--hidden-import=${m}`).join(' ');

const pyinstallerCmd = [
  'python -m PyInstaller',
  '--onedir',
  '--name DC_Submittal_Review_Backend',
  `--add-data=app${sep}app`,
  `--add-data=static${sep}static`,
  hiddenImports,
  '--noconfirm',
  'electron_launcher.py',
].join(' ');

run(pyinstallerCmd, { cwd: BACKEND });

// Step 5: Move output to dist/backend
step('Moving sidecar to dist/backend');
fs.rmSync(DIST_BACKEND, { recursive: true, force: true });
fs.cpSync(
  path.join(BACKEND, 'dist', 'DC_Submittal_Review_Backend'),
  DIST_BACKEND,
  { recursive: true }
);

// Clean up PyInstaller artifacts in backend/
for (const dir of ['build', 'dist']) {
  fs.rmSync(path.join(BACKEND, dir), { recursive: true, force: true });
}
fs.rmSync(path.join(BACKEND, 'DC_Submittal_Review_Backend.spec'), { force: true });

step('Backend sidecar built successfully');
console.log(`  Output: ${DIST_BACKEND}`);
console.log('  Run "electron-builder" to package the desktop app.');
