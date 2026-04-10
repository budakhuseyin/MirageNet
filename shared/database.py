import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from project root
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(ENV_PATH)

DB_TYPE = os.getenv('DB_TYPE', 'sqlite').lower()

# Database Query Placeholder (? for SQLite, %s for PostgreSQL)
PH = "?" if DB_TYPE == 'sqlite' else "%s"

def get_connection():
    """Returns a connection object based on DB_TYPE."""
    if DB_TYPE == 'postgres':
        import psycopg2
        return psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST', '127.0.0.1'),
            port=os.getenv('DB_PORT', '5432')
        )
    else:
        DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        DB_PATH = os.path.join(DB_DIR, 'miragenet.db')
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)
        return sqlite3.connect(DB_PATH, timeout=10)

def _offline_geoip_estimate(ip):
    """Fallback for offline location estimation."""
    try:
        first_octet = int(ip.split('.')[0])
    except (IndexError, ValueError):
        return "??", "Unknown", 0.0, 0.0

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
    """Fetched location data with a 30-minute DB cache."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Determine time comparison syntax
        time_filter = "datetime('now', '-30 minutes')" if DB_TYPE == 'sqlite' else "NOW() - INTERVAL '30 minutes'"
        
        query = f'''
            SELECT country_code, city, latitude, longitude 
            FROM attack_logs 
            WHERE ip_address = {PH} AND timestamp >= {time_filter}
            ORDER BY id DESC LIMIT 1
        '''
        cursor.execute(query, (ip,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            print(f"[*] GeoIP Cache Hit: {ip} (reusing previous data)")
            return row[0], row[1], row[2], row[3]
            
    except Exception as e:
        print(f"[!] GeoIP Cache Check Failed ({e})")

    # Local IP bypass
    try:
        if ip in ("127.0.0.1", "::1", "localhost") or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
            return "TR", "Local/Internal", 41.0082, 28.9784

        # Online API lookup
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

    return _offline_geoip_estimate(ip)

def init_db():
    """Initializes the database schema if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # SQLite uses AUTOINCREMENT, Postgres uses SERIAL/IDENTITY
    column_id = "id INTEGER PRIMARY KEY AUTOINCREMENT" if DB_TYPE == 'sqlite' else "id SERIAL PRIMARY KEY"
    
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS attack_logs (
            {column_id},
            timestamp TIMESTAMP,
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
    """Logs an attack event into the selected database."""
    iso_code, city, lat, lon = get_location_data(ip_address)
    
    conn = get_connection()
    cursor = conn.cursor()
    # Postgres handles datetime objects better directly, but we'll stick to string for compatibility if needed.
    # However, Django expects standard formats.
    timestamp = datetime.now()
    
    query = f'''
        INSERT INTO attack_logs (
            timestamp, ip_address, port, module, username, password, 
            user_agent, session_id, event_data, response_data, 
            country_code, city, latitude, longitude
        )
        VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})
    '''
    
    data = (timestamp, ip_address, port, module, username, password, 
            user_agent, session_id, event_data, response_data, 
            iso_code, city, lat, lon)
            
    cursor.execute(query, data)
    conn.commit()
    conn.close()

def get_attempt_count(ip_address, session_id, module):
    """Returns total attempts for a specific IP/session/module combo."""
    conn = get_connection()
    cursor = conn.cursor()
    query = f'''
        SELECT COUNT(*) FROM attack_logs 
        WHERE ip_address = {PH} AND session_id = {PH} AND module = {PH}
    '''
    cursor.execute(query, (ip_address, session_id, module))
    count = cursor.fetchone()[0]
    conn.close()
    return count

if __name__ == "__main__":
    init_db()
    print(f"[*] Database initialized in {DB_TYPE.upper()} mode.")