import threading
import socket
import paramiko
import sys
import os
import uuid

# Shared modüllerine erişim
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '../../'))
sys.path.append(PROJECT_ROOT)

from shared.database import log_attack, get_attempt_count

# RSA Key yükleme
HOST_KEY = paramiko.RSAKey(filename=os.path.join(CURRENT_DIR, 'rsa_key'))
PORT = 2222 # Test için 2222, canlıda 22 yapılır

class MirageSSHServer(paramiko.ServerInterface):
    def __init__(self, client_ip, session_id):
        self.event = threading.Event()
        self.client_ip = client_ip
        self.session_id = session_id

    def check_auth_password(self, username, password):
        # Kayıt atarken "SSH-Login" kullanıyoruz
        log_attack(
            self.client_ip, 22, "SSH-Login", 
            username, password, "SSH-Client", self.session_id
        )
        
        # Sayarken de "SSH-Login" olduğunu belirtmemiz şart!
        # BURAYI GÜNCELLE:
        attempts = get_attempt_count(self.client_ip, self.session_id, "SSH-Login")
        
        if attempts >= 2: 
            print(f"[*] SSH Access Granted for {username} [SID: {self.session_id}]")
            return paramiko.AUTH_SUCCESSFUL
        
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

def handle_connection(client_sock, client_addr):
    session_id = str(uuid.uuid4())[:8]
    print(f"[!] New SSH Connection: {client_addr[0]} [SID: {session_id}]")
    
    transport = paramiko.Transport(client_sock)
    transport.add_server_key(HOST_KEY)
    
    server = MirageSSHServer(client_addr[0], session_id)
    try:
        transport.start_server(server=server)
    except paramiko.SSHException:
        return

    chan = transport.accept(20)
    if chan is None:
        return

    server.event.wait(10)
    if not server.event.is_set():
        chan.close()
        return

    # Sahte Terminal Karşılaması
    chan.send("\r\nWelcome to Ubuntu 22.04.3 LTS (GNU/Linux 5.15.0-84-generic x86_64)\r\n\r\n")
    
    while True:
        chan.send("root@ubuntu:~# ")
        command = ""
        while not command.endswith("\r"):
            char = chan.recv(1024).decode('utf-8', errors='ignore')
            if not char:
                return
            chan.send(char) # Echo back
            command += char
        
        command = command.strip()
        chan.send("\r\n")
        
        if command in ["exit", "quit"]:
            chan.close()
            break
        
        # Komutu veritabanına "Input" olarak kaydet
        log_attack(
            client_addr[0], 22, "SSH-Command", 
            "root", f"CMD: {command}", "SSH-Terminal", session_id
        )

        # Sahte cevaplar (Simulation Logic)
        if command == "whoami":
            chan.send("root\r\n")
        elif command == "ls":
            chan.send("Desktop  Documents  Downloads  snap\r\n")
        elif command == "":
            pass
        else:
            chan.send(f"bash: {command}: command not found\r\n")

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