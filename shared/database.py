import sqlite3
import os
from datetime import datetime

# Dosya yolları
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'miragenet.db')

if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

def _offline_geoip_estimate(ip):
    """İnternet olmadığında IP aralığından kaba tahmini konum döner."""
    try:
        first_octet = int(ip.split('.')[0])
    except (IndexError, ValueError):
        return "??", "Unknown", 0.0, 0.0

    # Bilinen büyük bloklar (kaba tahmin, sadece fallback için)
    if 1 <= first_octet <= 50:
        return "US", "North America", 37.09, -95.71
    elif 51 <= first_octet <= 100:
        return "EU", "Europe", 50.11, 8.68
    elif 101 <= first_octet <= 130:
        return "AP", "Asia-Pacific", 35.68, 139.69
    elif 131 <= first_octet <= 160:
        return "US", "North America", 37.09, -95.71
    elif 161 <= first_octet <= 190:
        return "EU", "Europe", 48.85, 2.35
    elif 191 <= first_octet <= 200:
        return "BR", "South America", -14.23, -51.92
    elif 200 <= first_octet <= 210:
        return "BR", "Brazil", -15.77, -47.92
    elif 210 <= first_octet <= 220:
        return "JP", "Asia", 35.68, 139.69
    elif 177 <= first_octet <= 179:
        return "BR", "Brazil", -23.54, -46.63
    elif 196 <= first_octet <= 197:
        return "ZA", "Africa", -30.55, 22.93
    else:
        return "??", "Unknown", 20.0, 0.0


def get_location_data(ip):
    """
    IP adresinden koordinat ve şehir bilgilerini döner. 
    Son 30 dakika içinde bu IP için bir kayıt varsa API isteği atmaz (Cache).
    """
    # 1. Önce veritabanında son 30 dakika içinde bir kayıt var mı kontrol et
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        
        # SQLite'da tarih karşılaştırması: Son 30 dakika
        # NOT: log_attack'da timestamp'i YYYY-MM-DD HH:MM:SS formatında kaydettiğimiz için datetime('now', '-30 minutes') ile kıyaslayabiliriz.
        cursor.execute('''
            SELECT country_code, city, latitude, longitude 
            FROM attack_logs 
            WHERE ip_address = ? AND timestamp >= datetime('now', '-30 minutes')
            ORDER BY id DESC LIMIT 1
        ''', (ip,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            print(f"[*] GeoIP Cache Hit: {ip} (reusing previous data)")
            return row[0], row[1], row[2], row[3]
            
    except Exception as e:
        print(f"[!] GeoIP Cache Check Failed ({e})")

    # 2. Localhost veya yerel ağ ise sabit bir nokta dön
    try:
        if ip in ("127.0.0.1", "::1", "localhost") or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
            return "TR", "Local/Internal", 41.0082, 28.9784

        # 3. ip-api.com ücretsiz HTTP API (kurulum gerektirmez, saniyede 45 istek)
        import urllib.request
        url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,lat,lon"
        req = urllib.request.Request(url, headers={"User-Agent": "MirageNet/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            import json as _json
            data = _json.loads(resp.read().decode())
            if data.get("status") == "success":
                return (
                    data.get("countryCode", "??"),
                    data.get("city", "Unknown"),
                    float(data.get("lat", 0.0)),
                    float(data.get("lon", 0.0))
                )
    except Exception as e:
        print(f"[!] GeoIP Online Lookup Failed ({e}), using offline estimate...")

    # 4. Fallback: kaba IP aralığı tahmini
    return _offline_geoip_estimate(ip)


def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
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
    
    conn = sqlite3.connect(DB_PATH, timeout=10)
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
    conn = sqlite3.connect(DB_PATH, timeout=10)
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