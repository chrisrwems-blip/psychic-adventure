const path = require('path');

const BACKEND_PORT = 8000;
const VITE_PORT = 5173;
const HEALTH_URL = `http://localhost:${BACKEND_PORT}/api/health`;
const BACKEND_EXE_NAME = 'DC_Submittal_Review_Backend';

const ROOT = path.resolve(__dirname, '..', '..');
const BACKEND_DIR = path.join(ROOT, 'backend');
const FRONTEND_DIR = path.join(ROOT, 'frontend');
const ELECTRON_DIR = path.join(ROOT, 'electron');

module.exports = {
  BACKEND_PORT,
  VITE_PORT,
  HEALTH_URL,
  BACKEND_EXE_NAME,
  ROOT,
  BACKEND_DIR,
  FRONTEND_DIR,
  ELECTRON_DIR,
};
