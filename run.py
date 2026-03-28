"""Single-process launcher — runs both backend and frontend from one script."""
import os
import sys
import subprocess
import time
import threading
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
FRONTEND_DIR = os.path.join(ROOT, "frontend")


def install_deps():
    """Install all dependencies if needed."""
    print("[1/2] Checking Python dependencies...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print("[2/2] Checking frontend dependencies...")
    if not os.path.exists(os.path.join(FRONTEND_DIR, "node_modules")):
        subprocess.run(
            ["npm", "install", "--silent"],
            cwd=FRONTEND_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True,
        )
    print("       Dependencies OK.")


def run_backend():
    """Run the FastAPI backend."""
    print("       Starting backend on http://localhost:8000 ...")
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=BACKEND_DIR,
    )


def run_frontend():
    """Run the Vite frontend dev server."""
    print("       Starting frontend on http://localhost:5173 ...")
    subprocess.run(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        shell=True,
    )


def open_browser():
    """Wait for servers to start, then open browser."""
    time.sleep(5)
    print()
    print("=" * 50)
    print("  DC Submittal Review Platform is running!")
    print("  Opening browser to http://localhost:5173")
    print()
    print("  Close this window to stop the application.")
    print("=" * 50)
    print()
    webbrowser.open("http://localhost:5173")


if __name__ == "__main__":
    print()
    print("=" * 50)
    print("  DC Submittal Review Platform")
    print("  Starting up...")
    print("=" * 50)
    print()

    install_deps()

    # Run backend and frontend in threads
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    frontend_thread = threading.Thread(target=run_frontend, daemon=True)
    browser_thread = threading.Thread(target=open_browser, daemon=True)

    backend_thread.start()
    frontend_thread.start()
    browser_thread.start()

    # Keep main thread alive — closing the window kills everything
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
