import sys
import os
import subprocess
import time

# Absolute paths to ensure it works regardless of where it's called
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTTP_LISTENER = os.path.join(BASE_DIR, 'ports', 'port_80_http', 'listener.py')
SSH_LISTENER = os.path.join(BASE_DIR, 'ports', 'port_22_ssh', 'ssh_listener.py')
DJANGO_MANAGE = os.path.join(BASE_DIR, 'web_dashboard', 'manage.py')
WSGI_SERVER = os.path.join(BASE_DIR, 'web_dashboard', 'wsgi_server.py')

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
    
    active_processes = {}
    
    # 2. Start Django Dashboard (Production with Waitress)
    django_proc = run_process(
        "Web Dashboard (Waitress)", 
        [sys.executable, WSGI_SERVER], 
        cwd=os.path.join(BASE_DIR, "web_dashboard")
    )
    if django_proc: active_processes["Web Dashboard"] = django_proc
    
    time.sleep(2) # Give django a moment to start
    print("-" * 50)
    
    # 3. Start HTTP Honeypot
    http_proc = run_process(
        "HTTP Sensor (Port 80/8080)", 
        [sys.executable, HTTP_LISTENER], 
        cwd=BASE_DIR
    )
    if http_proc: active_processes["HTTP Sensor"] = http_proc
    
    time.sleep(1)
    
    # 4. Start SSH Honeypot
    ssh_proc = run_process(
        "SSH Sensor (Port 22/2222)", 
        [sys.executable, SSH_LISTENER], 
        cwd=BASE_DIR
    )
    if ssh_proc: active_processes["SSH Sensor"] = ssh_proc
    
    print("-" * 50)
    print("\n[+] ALL SENSORS AND DASHBOARD ARE RUNNING!")
    print("[+] Access Mirage Control Center at: http://127.0.0.1:8000/mirage-control-center/")
    print("[!] Press Ctrl+C to stop all services cleanly.\n")
    print("==================================================")
    
    try:
        # 5. Continuous Monitoring Loop
        while True:
            for name, p in active_processes.items():
                if p.poll() is not None:
                    print(f"\n[!] CRITICAL ERROR: {name} has stopped unexpectedly (Exit Code: {p.returncode})!")
                    raise Exception(f"{name} failure")
            time.sleep(1) # Check every second
            
    except (KeyboardInterrupt, Exception) as e:
        if isinstance(e, KeyboardInterrupt):
            print("\n\n[*] KeyboardInterrupt detected. Shutting down MirageNet...")
        else:
            print(f"\n[*] Shutting down due to service failure: {e}")
            
        for name, p in active_processes.items():
            print(f"[*] Terminating {name} (PID: {p.pid})...")
            p.terminate() 
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
        print("[+] MirageNet stopped.")

if __name__ == "__main__":
    main()
