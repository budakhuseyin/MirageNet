import sqlite3
import json
import os
import datetime

# MirageNet Data Export Script
# Converts the attack_logs table from SQLite to a JSON file for analysis or migration.

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'miragenet.db')
EXPORT_DIR = os.path.join(BASE_DIR, 'exports')

def export_to_json():
    """Reads attack logs using a streaming approach to support massive datasets without RAM issues."""
    if not os.path.exists(DB_PATH):
        print(f"[!] Database not found at {DB_PATH}")
        return

    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)
        print(f"[*] Created export directory: {EXPORT_DIR}")

    # Connect to the database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        print("[*] Starting high-performance extraction (Streaming mode)...")
        # Optimization: Use an iterator instead of fetchall()
        cursor.execute("SELECT * FROM attack_logs ORDER BY timestamp DESC")

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"miragenet_stream_export_{timestamp}.json"
        filepath = os.path.join(EXPORT_DIR, filename)

        # Open file and write JSON array manually to save memory
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("[\n")
            
            count = 0
            for row in cursor:
                if count > 0:
                    f.write(",\n")
                
                # Convert row to dict and write one at a time
                json.dump(dict(row), f, ensure_ascii=False)
                count += 1
                
                if count % 1000 == 0:
                    print(f"[*] Processed {count} records...")

            f.write("\n]")

        print(f"[+] Success! {count} records streamed to:")
        print(f"    {filepath}")

    except Exception as e:
        print(f"[!!] Streaming export failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("-" * 45)
    print(" MirageNet JSON Data Export Utility")
    print("-" * 45)
    export_to_json()
    print("-" * 45)
