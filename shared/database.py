import sqlite3
import os
from datetime import datetime
import geoip2.database

# Dosya yolları
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'miragenet.db')
GEOIP_PATH = os.path.join(DB_DIR, 'geolite2-city-ipv4.mmdb')

if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

def get_location_data(ip):
    """IP adresinden koordinat ve şehir bilgilerini döner."""
    try:
        # Yerel ağ veya localhost ise sabit bir nokta dön (Örn: İstanbul)
        if ip == "127.0.0.1" or ip.startswith("192.168"):
            return "TR", "Local/Internal", 41.0082, 28.9784
            
        if os.path.exists(GEOIP_PATH):
            with geoip2.database.Reader(GEOIP_PATH) as reader:
                response = reader.city(ip)
                return (
                    response.country.iso_code, 
                    response.city.name if response.city.name else "Unknown",
                    response.location.latitude, 
                    response.location.longitude
                )
    except Exception as e:
        print(f"[!] GeoIP Lookup Error: {e}")
    
    return "??", "Unknown", 0.0, 0.0

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabloyu yeni sütunlarla (city, lat, lon) oluştur/güncelle
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
            event_data TEXT,
            response_data TEXT,
            country_code TEXT,
            city TEXT,
            latitude REAL,
            longitude REAL
        )
    ''')
    conn.commit()
    conn.close()

def log_attack(ip_address, port, module, username, password, user_agent, session_id, event_data="", response_data="", country_code="??"):
    # Önce konum verilerini çek
    iso_code, city, lat, lon = get_location_data(ip_address)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO attack_logs (
            timestamp, ip_address, port, module, username, password, 
            user_agent, session_id, event_data, response_data, 
            country_code, city, latitude, longitude
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, ip_address, port, module, username, password, 
          user_agent, session_id, event_data, response_data, 
          iso_code, city, lat, lon))
    
    conn.commit()
    conn.close()

def get_attempt_count(ip_address, session_id, module):
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