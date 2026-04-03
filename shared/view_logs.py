import sqlite3
import os

# Veritabanı yolu
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'miragenet.db')

def display_logs():
    if not os.path.exists(DB_PATH):
        print("[-] Database file not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tüm sütunları çekiyoruz
    cursor.execute("SELECT * FROM attack_logs ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    
    if not rows:
        print("[!] Database is empty.")
    else:
        # Başlık kısmına yeni sütunları ekledik
        header = f"{'ID':<4} | {'TIMESTAMP':<19} | {'IP':<14} | {'MOD':<10} | {'SID':<8} | {'EVENT':<20} | {'RESP':<20}"
        print(header)
        print("-" * len(header))
        
        for row in rows:
            # row index haritası:
            # 0:id, 1:ts, 2:ip, 3:port, 4:mod, 5:user, 6:pass, 7:ua, 8:sid, 9:event, 10:resp, 11:geo
            
            # Verileri daha okunabilir kılmak için uzun metinleri kırpıyoruz
            event = (row[9][:17] + '..') if row[9] and len(row[9]) > 17 else (row[9] or "")
            resp = (row[10][:17] + '..').replace('\n', ' ') if row[10] and len(row[10]) > 17 else (row[10] or "").replace('\n', ' ')
            
            print(f"{row[0]:<4} | {row[1]:<19} | {row[2]:<14} | {row[4]:<10} | {row[8]:<8} | {event:<20} | {resp:<20}")
            
    conn.close()

if __name__ == "__main__":
    display_logs()