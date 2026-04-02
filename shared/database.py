import sqlite3
import os
from datetime import datetime

# Veri tabanı dosyasının nerede duracağını belirliyoruz (ana dizindeki data klasörü)
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'miragenet.db')

# Eğer data klasörü yoksa otomatik oluştur
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

def init_db():
    """Veri tabanını ve gerekli tabloları oluşturur."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Saldırı loglarını tutacağımız ana tablo
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attack_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            ip_address TEXT,
            port INTEGER,
            module TEXT,
            username TEXT,
            password TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("[*] Database initialized at:", DB_PATH)

def log_attack(ip_address, port, module, username, password):
    """Yakalanan saldırı verilerini veri tabanına kaydeder."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO attack_logs (timestamp, ip_address, port, module, username, password)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (timestamp, ip_address, port, module, username, password))
    
    conn.commit()
    conn.close()
    print(f"[+] Attack logged to database from IP: {ip_address}")

# Bu dosya doğrudan çalıştırılırsa tabloyu kur
if __name__ == "__main__":
    init_db()