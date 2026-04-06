import sys
import os
import subprocess
import time

# Absolute paths to ensure it works regardless of where it's called
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTTP_LISTENER = os.path.join(BASE_DIR, 'ports', 'port_80_http', 'listener.py')
SSH_LISTENER = os.path.join(BASE_DIR, 'ports', 'port_22_ssh', 'ssh_listener.py')
DJANGO_MANAGE = os.path.join(BASE_DIR, 'web_dashboard', 'manage.py')

def init_database():
    print("[*] Checking / Initializing database...")
    # Add BASE_DIR to sys.path so we can import shared
    sys.path.insert(0, BASE_DIR)
    from shared.database import init_db
    init_db()
    print("[+] Database check complete.")

def run_process(name, cmd, cwd=None):
    print(f"[*] Starting {name}...")
    try:
        # Start the process in the background
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=sys.stdout, # Route output directly to the main terminal
            stderr=sys.stderr,
            text=True
        )
        return process
    except Exception as e:
        print(f"[!] Failed to start {name}: {e}")
        return None

def main():
    print("==================================================")
    print("             MIRAGENET SYSTEM STARTUP             ")
    print("==================================================\n")
    
    # 1. Initialize Database First
    init_database()
    print("-" * 50)
    
    processes = []
    
    # 2. Start Django Dashboard 
    django_proc = run_process(
        "Web Dashboard", 
        [sys.executable, DJANGO_MANAGE, "runserver", "0.0.0.0:8000"], 
        cwd=os.path.join(BASE_DIR, "web_dashboard")
    )
    if django_proc: processes.append(django_proc)
    
    time.sleep(2) # Give django a moment to start
    print("-" * 50)
    
    # 3. Start HTTP Honeypot
    http_proc = run_process(
        "HTTP Sensor (Port 80/8080)", 
        [sys.executable, HTTP_LISTENER], 
        cwd=BASE_DIR
    )
    if http_proc: processes.append(http_proc)
    
    time.sleep(1)
    
    # 4. Start SSH Honeypot
    ssh_proc = run_process(
        "SSH Sensor (Port 22/2222)", 
        [sys.executable, SSH_LISTENER], 
        cwd=BASE_DIR
    )
    if ssh_proc: processes.append(ssh_proc)
    
    print("-" * 50)
    print("\n[+] ALL SENSORS AND DASHBOARD ARE RUNNING!")
    print("[+] Access Dashboard at: http://127.0.0.1:8000")
    print("[!] Press Ctrl+C to stop all services cleanly.\n")
    print("==================================================")
    
    try:
        # Keep the main script running so the background processes stay alive.
        # Wait for the processes, if one dies, we still wait.
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("\n\n[*] KeyboardInterrupt detected. Shutting down MirageNet...")
        for p in processes:
            print(f"[*] Terminating Process PID: {p.pid}...")
            p.terminate() # or p.kill() on Windows if terminate is ignored
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
        print("[+] MirageNet stopped gracefully.")

if __name__ == "__main__":
    main()
