import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'miragenet.db')

def display_logs():
    if not os.path.exists(DB_PATH):
        print("[-] Database file not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM attack_logs")
    rows = cursor.fetchall()
    
    if not rows:
        print("[!] Database is empty.")
    else:
        print(f"{'ID':<5} | {'TIMESTAMP':<20} | {'IP':<15} | {'PORT':<5} | {'MODULE':<15} | {'USERNAME':<15} | {'PASSWORD':<15}")
        print("-" * 105)
        for row in rows:
            # row: (id, timestamp, ip, port, module, user, pass, user_agent)
            print(f"{row[0]:<5} | {row[1]:<20} | {row[2]:<15} | {row[3]:<5} | {row[4]:<15} | {row[5]:<15} | {row[6]:<15}")
            
    conn.close()

if __name__ == "__main__":
    display_logs()