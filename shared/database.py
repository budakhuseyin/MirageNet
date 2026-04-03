import sqlite3
import os
from datetime import datetime

# Dosya yollarını garantiye alıyoruz
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'miragenet.db')

if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attack_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            ip_address TEXT,
            port INTEGER,
            module TEXT,
            username TEXT,
            password TEXT,
            user_agent TEXT,
            session_id TEXT,
            event_data TEXT,     -- Girdi (Komut, Dosya adı vb.)
            response_data TEXT,  -- Çıktı (Sistemin verdiği cevap)
            country_code TEXT    -- Harita için (TR, US vb.)
        )
    ''')
    conn.commit()
    conn.close()

def log_attack(ip_address, port, module, username, password, user_agent, session_id, event_data="", response_data="", country_code="??"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO attack_logs (timestamp, ip_address, port, module, username, password, user_agent, session_id, event_data, response_data, country_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, ip_address, port, module, username, password, user_agent, session_id, event_data, response_data, country_code))
    
    conn.commit()
    conn.close()

def get_attempt_count(ip_address, session_id, module):
    """Belirli bir IP, Session ve MODÜL kombinasyonunun deneme sayısını döndürür."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM attack_logs 
        WHERE ip_address = ? AND session_id = ? AND module = ?
    ''', (ip_address, session_id, module))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count

if __name__ == "__main__":
    init_db()