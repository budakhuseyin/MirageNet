import threading
import socket
import paramiko
import sys
import os
import uuid

# Proje kök dizinine erişim ayarları
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '../../'))
sys.path.append(PROJECT_ROOT)

from shared.database import log_attack, get_attempt_count

# RSA Key yükleme (Hata almamak için yol sabitlendi)
HOST_KEY = paramiko.RSAKey(filename=os.path.join(CURRENT_DIR, 'rsa_key'))
PORT = 2222 

class MirageSSHServer(paramiko.ServerInterface):
    def __init__(self, client_ip, session_id):
        self.event = threading.Event()
        self.client_ip = client_ip
        self.session_id = session_id

    def check_auth_password(self, username, password):
        # Her login denemesini yeni şemaya göre kaydet
        log_attack(
            ip_address=self.client_ip, 
            port=22, 
            module="SSH-Login", 
            username=username, 
            password=password, 
            user_agent="SSH-Client", 
            session_id=self.session_id,
            event_data=f"Auth Attempt: {username}",
            response_data="Permission denied",
            country_code="??" # İleride GeoIP ile güncellenecek
        )
        
        # Oturumdaki deneme sayısını kontrol et
        attempts = get_attempt_count(self.client_ip, self.session_id, "SSH-Login")
        
        # Test için 2, gerçekte 10+ yapılabilir
        if attempts >= 2: 
            print(f"[*] SSH Access Granted for {username} [SID: {self.session_id}]")
            return paramiko.AUTH_SUCCESSFUL
        
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        if kind == 'session': return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

def handle_connection(client_sock, client_addr):
    session_id = str(uuid.uuid4())[:8]
    transport = paramiko.Transport(client_sock)
    transport.add_server_key(HOST_KEY)
    
    server = MirageSSHServer(client_addr[0], session_id)
    try:
        transport.start_server(server=server)
    except Exception:
        return

    chan = transport.accept(20)
    if chan is None: return

    server.event.wait(10)
    if not server.event.is_set():
        chan.close()
        return

    # --- TİYATRO BAŞLIYOR: SAHTE TERMİNAL ---
    chan.send("\r\nWelcome to Ubuntu 22.04.3 LTS (GNU/Linux 5.15.0-84-generic x86_64)\r\n\r\n")
    
    while True:
        chan.send("root@ubuntu:~# ")
        command = ""
        while not command.endswith("\r"):
            char = chan.recv(1024).decode('utf-8', errors='ignore')
            if not char: return
            chan.send(char) # Echo back (Saldırganın yazdığını görmesi için)
            command += char
        
        command = command.strip()
        chan.send("\r\n")
        
        if command in ["exit", "quit"]:
            chan.close()
            break
        
        # --- KOMUT SİMÜLASYON MANTIĞI ---
        response = ""
        
        if command == "whoami":
            response = "root\r\n"
        elif command == "ls":
            response = "Desktop  Documents  Downloads  snap  web-app  backup.sql\r\n"
        elif command == "id":
            response = "uid=0(root) gid=0(root) groups=0(root)\r\n"
        elif command == "uname -a":
            response = "Linux ubuntu 5.15.0-84-generic #93-Ubuntu SMP Tue Sep 5 17:16:10 UTC 2023 x86_64 x86_64 GNU/Linux\r\n"
        elif command == "cat /etc/passwd":
            response = "root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\nbin:x:2:2:bin:/bin:/usr/sbin/nologin\n"
        elif command.startswith("cd"):
            response = "" # Başarılı geçmiş gibi sessiz kal
        elif "sudo" in command:
            response = "[sudo] password for root: \r\nSorry, try again.\r\n"
        elif command == "":
            response = ""
        else:
            response = f"bash: {command}: command not found\r\n"

        # Çıktıyı gönder
        chan.send(response)

        # ADLİ BİLİŞİM KAYDI: Girdi ve Çıktıyı ayrı sütunlara logla
        log_attack(
            ip_address=client_addr[0],
            port=22,
            module="SSH-Command",
            username="root",
            password="N/A",
            user_agent="SSH-Terminal",
            session_id=session_id,
            event_data=command,      # Ne yazdı?
            response_data=response,   # Ne cevap verdik?
            country_code="??"
        )

def start_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', PORT))
    sock.listen(100)
    print(f"[*] MirageNet SSH Sensor listening on Port: {PORT}")
    
    while True:
        client, addr = sock.accept()
        threading.Thread(target=handle_connection, args=(client, addr)).start()

if __name__ == "__main__":
    start_server()