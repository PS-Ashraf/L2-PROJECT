import subprocess
import os
import time
import sys

def main():
    print("Starting Daily Planner Agent...")
    print("Please wait while we initialize the backend and frontend...\n")

    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")

    # Start Backend
    # On Windows, we can use the venv python directly if it exists, otherwise we just use python
    venv_python = os.path.join(root_dir, "venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        backend_cmd = f'"{venv_python}" -m uvicorn main:app --reload'
        backend_cwd = os.path.join(root_dir, "backend")
    else:
        # Fallback to creating venv and running
        backend_cmd = 'python -m venv venv && venv\\Scripts\\activate.bat && pip install -r requirements.txt && cd backend && uvicorn main:app --reload'
        backend_cwd = root_dir

    backend_process = subprocess.Popen(
        backend_cmd,
        cwd=backend_cwd,
        shell=True
    )

    # Start Frontend
    frontend_cmd = 'npm install && npm run dev'
    frontend_process = subprocess.Popen(
        frontend_cmd,
        cwd=frontend_dir,
        shell=True
    )

    # Give them a few seconds to start up
    time.sleep(4)

    print("=" * 60)
    print("App is successfully running in the background!")
    print("=" * 60)
    print("\n   CLICK HERE TO OPEN APP: http://localhost:5173\n")
    print("   (Backend API is running at: http://localhost:8000)")
    print("\n" + "=" * 60)
    print("Press Ctrl+C in this terminal to stop both servers.")
    
    try:
        # Keep the script running so the background processes stay alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping servers...")
        # Kill the child processes
        subprocess.run(f"taskkill /F /T /PID {backend_process.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(f"taskkill /F /T /PID {frontend_process.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Servers stopped successfully. Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
