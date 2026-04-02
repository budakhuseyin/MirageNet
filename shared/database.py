import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'miragenet.db')

if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # user_agent sütununu ekledik
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attack_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            ip_address TEXT,
            port INTEGER,
            module TEXT,
            username TEXT,
            password TEXT,
            user_agent TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("[*] Database initialized at:", DB_PATH)

# Parametrelere user_agent eklendi
def log_attack(ip_address, port, module, username, password, user_agent):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # INSERT sorgusuna user_agent dahil edildi
    cursor.execute('''
        INSERT INTO attack_logs (timestamp, ip_address, port, module, username, password, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, ip_address, port, module, username, password, user_agent))
    
    conn.commit()
    conn.close()
    print(f"[+] Attack logged to database from IP: {ip_address}")

if __name__ == "__main__":
    init_db()