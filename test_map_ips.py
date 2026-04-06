import sys
import time
import random
import uuid
import os

# Sisteme giden yollari dahil et
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.database import log_attack

test_ips = [
    ("8.8.8.8", "22", "SSH-Login", "root", "toor_-US"),            # Amerika
    ("51.140.231.1", "80", "HTTP-Scanner", "admin", "admin_-UK"),    # Birlesik Krallik
    ("114.160.10.1", "22", "SSH-Login", "root", "pass123_-JP"),     # Japonya
    ("177.45.2.1", "80", "HTTP-Scanner", "-", "guest_-BR"),         # Brezilya
    ("139.130.4.5", "22", "SSH-Login", "admin", "123456_-AU"),      # Avustralya
    ("196.223.15.1", "80", "HTTP-Scanner", "-", "admin_-ZA"),       # Guney Afrika
]

def main():
    print("[*] MirageNet Harita Testi Başlıyor...")
    print("[*] Dashboard açık olsun (World Map). Her 4 saniyede 1 IP eklenecek...\n")
    
    for ip, port, module, usr, pwd in test_ips:
        session_id = f"TEST-GEO-{str(uuid.uuid4())[:8]}"
        user_agent = "Python-Urllib/3.8"
        
        # Gercek DB insert islemi
        log_attack(
            ip_address=ip,
            port=int(port),
            module=module,
            username=usr,
            password=pwd,
            user_agent=user_agent,
            session_id=session_id
        )
        
        print(f"[+] Eklendi: {ip} -> DB'ye yazildi. Haritada radar gormeniz lazim.")
        
        # Radar efektinin HTMX poll suresi kadar (3-4 sn) beklemesini sagla
        time.sleep(4)

    print("\n[+] Tum test IP'leri basariyla gönderildi!")

if __name__ == "__main__":
    main()
