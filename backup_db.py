import os
import shutil
import datetime
import glob

# MirageNet Backup Script
# This script creates a timestamped copy of the database and manages rotation.

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'miragenet.db')
PAYLOADS_DIR = os.path.join(BASE_DIR, 'data', 'payloads')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')

# Configuration
MAX_BACKUPS = 7  # Keep last 7 backups

def create_backup():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"[*] Created backup directory: {BACKUP_DIR}")

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    # 1. Backup Database
    if os.path.exists(DB_PATH):
        db_backup_name = f"miragenet_{timestamp}.db"
        db_backup_path = os.path.join(BACKUP_DIR, db_backup_name)
        shutil.copy2(DB_PATH, db_backup_path)
        print(f"[+] Database backed up to: {db_backup_name}")
    else:
        print(f"[!] Database not found at {DB_PATH}. Skipping.")

    # 2. Backup Payloads (Optional - Zip them if exists)
    if os.path.exists(PAYLOADS_DIR) and os.listdir(PAYLOADS_DIR):
        payloads_backup_name = f"payloads_{timestamp}"
        payloads_backup_path = os.path.join(BACKUP_DIR, payloads_backup_name)
        shutil.make_archive(payloads_backup_path, 'zip', PAYLOADS_DIR)
        print(f"[+] Payloads backed up to: {payloads_backup_name}.zip")

def rotate_backups():
    print(f"[*] Rotating backups (keeping last {MAX_BACKUPS})...")
    
    # Get all .db backups sorted by time
    db_backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "miragenet_*.db")), key=os.path.getmtime)
    
    while len(db_backups) > MAX_BACKUPS:
        oldest = db_backups.pop(0)
        try:
            os.remove(oldest)
            print(f"[-] Deleted old database backup: {os.path.basename(oldest)}")
        except Exception as e:
            print(f"[!] Error deleting {oldest}: {e}")

    # Get all .zip payloads sorted by time
    zip_backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "payloads_*.zip")), key=os.path.getmtime)
    
    while len(zip_backups) > MAX_BACKUPS:
        oldest = zip_backups.pop(0)
        try:
            os.remove(oldest)
            print(f"[-] Deleted old payloads backup: {os.path.basename(oldest)}")
        except Exception as e:
            print(f"[!] Error deleting {oldest}: {e}")

if __name__ == "__main__":
    print("-" * 40)
    print(f" MirageNet Backup Service - {datetime.datetime.now()}")
    print("-" * 40)
    
    try:
        create_backup()
        rotate_backups()
        print("[+] Backup process completed successfully.")
    except Exception as e:
        print(f"[!!] Backup failed: {e}")
    print("-" * 40)
