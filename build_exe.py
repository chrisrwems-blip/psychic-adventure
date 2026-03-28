"""Build script — creates a single Windows .exe from the entire application.

Run this on a Windows machine:
    python build_exe.py

It will:
1. Build the frontend (npm run build → static files)
2. Configure the backend to serve those static files
3. Bundle everything into a single .exe with PyInstaller
4. Output: dist/DC_Submittal_Review.exe

Requirements:
    pip install pyinstaller
    npm (for frontend build)
"""
import subprocess
import sys
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
FRONTEND = os.path.join(ROOT, "frontend")
DIST = os.path.join(ROOT, "dist")


def step(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


def build_frontend():
    step("Building frontend (React → static files)")
    subprocess.run(["npm", "install"], cwd=FRONTEND, shell=True, check=True)
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND, shell=True, check=True)

    # Copy built files to backend/static so the backend can serve them
    static_dir = os.path.join(BACKEND, "static")
    if os.path.exists(static_dir):
        shutil.rmtree(static_dir)
    shutil.copytree(os.path.join(FRONTEND, "dist"), static_dir)
    print(f"  Frontend built and copied to {static_dir}")


def create_production_app():
    """Create a production version of main.py that serves static files."""
    step("Creating production app (backend serves frontend)")

    prod_app = os.path.join(BACKEND, "app", "production.py")
    with open(prod_app, "w", encoding="utf-8") as f:
        f.write('# -*- coding: utf-8 -*-\n')
        f.write('''"""Production app - serves both API and frontend from a single process."""
import os
from app.main import app
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# Serve frontend static files
if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        """Serve the React app for any non-API route."""
        file_path = os.path.join(STATIC_DIR, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
''')
    print(f"  Created {prod_app}")


def create_launcher():
    """Create the entry point script for PyInstaller."""
    step("Creating launcher script")

    launcher = os.path.join(BACKEND, "launcher.py")
    with open(launcher, "w", encoding="utf-8") as f:
        f.write('''"""Single-exe launcher for DC Submittal Review Platform."""
import os
import sys
import webbrowser
import threading
import time

# Set the working directory to where the exe is
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

def open_browser():
    time.sleep(3)
    webbrowser.open("http://localhost:8000")

print("DC Submittal Review Platform")
print("Starting server...")
print("Browser will open automatically.")
print("Close this window to stop the application.")
print()

threading.Thread(target=open_browser, daemon=True).start()

import uvicorn
from app.production import app

uvicorn.run(app, host="0.0.0.0", port=8000)
''')
    print(f"  Created {launcher}")


def build_exe():
    step("Building .exe with PyInstaller")

    # PyInstaller spec
    subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "DC_Submittal_Review",
        "--add-data", f"app{os.pathsep}app",
        "--add-data", f"static{os.pathsep}static",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.http.h11_impl",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "app.main",
        "--hidden-import", "app.production",
        "--hidden-import", "app.database",
        "--hidden-import", "app.routers.projects",
        "--hidden-import", "app.routers.submittals",
        "--hidden-import", "app.routers.reviews",
        "--hidden-import", "app.routers.comments",
        "--hidden-import", "app.routers.emails",
        "--hidden-import", "sqlalchemy.dialects.sqlite",
        "--icon", "NONE",
        "launcher.py",
    ], cwd=BACKEND, check=True)

    # Move to dist folder at root
    os.makedirs(DIST, exist_ok=True)
    src = os.path.join(BACKEND, "dist", "DC_Submittal_Review.exe")
    dst = os.path.join(DIST, "DC_Submittal_Review.exe")
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"\n  SUCCESS: {dst}")
        print(f"  Size: {os.path.getsize(dst) / (1024*1024):.1f} MB")
    else:
        print("  ERROR: .exe not found after build")


def cleanup():
    step("Cleaning up build artifacts")
    for d in ["build", "dist", "__pycache__"]:
        path = os.path.join(BACKEND, d)
        if os.path.exists(path):
            shutil.rmtree(path)
    spec = os.path.join(BACKEND, "DC_Submittal_Review.spec")
    if os.path.exists(spec):
        os.remove(spec)


if __name__ == "__main__":
    print("\nDC Submittal Review Platform — Build Script")
    print("=" * 60)

    build_frontend()
    create_production_app()
    create_launcher()
    build_exe()

    print("\n" + "=" * 60)
    print("  BUILD COMPLETE")
    print(f"  Executable: {os.path.join(DIST, 'DC_Submittal_Review.exe')}")
    print()
    print("  To run: double-click DC_Submittal_Review.exe")
    print("  No Python, Node.js, or terminal needed.")
    print("=" * 60)
