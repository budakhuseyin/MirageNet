import http.server
import socketserver
import urllib.parse
import os
import sys
import uuid

# shared klasöründeki database modüllerini içe aktar
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from shared.database import log_attack, get_attempt_count

PORT = 8080 
DECOY_LOGIN = "decoys/wp-login.html"
DECOY_DASHBOARD = "decoys/wp-dashboard.html"
DECOY_EDITOR = "decoys/wp-theme-editor.html"

# Malware kayıt klasörü
PAYLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/payloads'))
if not os.path.exists(PAYLOAD_DIR):
    os.makedirs(PAYLOAD_DIR)

class HoneypotHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    
    def _set_headers(self, status_code=200, content_type='text/html; charset=utf-8'):
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.send_header('Server', 'Apache/2.4.41 (Ubuntu)') 
        self.end_headers()

    def do_GET(self):
        print(f"[!] GET Request: {self.client_address[0]} -> {self.path}")
        user_agent = self.headers.get('User-Agent', 'Unknown')

        # TUZAK 1: WordPress Login
        if "wp-login.php" in self.path:
            self._set_headers(200)
            with open(DECOY_LOGIN, "rb") as file:
                self.wfile.write(file.read())

        # TUZAK 2: Sahte .env Dosyası (Bilgi Sızdırma Simülasyonu)
        elif ".env" in self.path:
            log_attack(self.client_address[0], PORT, "HTTP-DOT-ENV", "N/A", "Attempted download", user_agent)
            self._set_headers(200, 'text/plain')
            fake_env = "DB_HOST=localhost\nDB_USER=root\nDB_PASS=S3cur3P@ssw0rd!\nAWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
            self.wfile.write(fake_env.encode())

        # TUZAK 3: phpMyAdmin Tarama Yakalayıcı
        elif "phpmyadmin" in self.path.lower():
            log_attack(self.client_address[0], PORT, "HTTP-PHPMYADMIN", "N/A", "Scanning", user_agent)
            self._set_headers(403)
            self.wfile.write(b"<h1>403 Forbidden: Access Denied</h1>")

        # Dashboard ve Editor Yolları
        elif self.path == "/wp-admin/" or self.path == "/wp-admin/index.php":
            self._set_headers(200)
            with open(DECOY_DASHBOARD, "rb") as file:
                self.wfile.write(file.read())
        elif "theme-editor.php" in self.path:
            self._set_headers(200)
            with open(DECOY_EDITOR, "rb") as file:
                self.wfile.write(file.read())
        else:
            self._set_headers(404)
            self.wfile.write(b"<h1>404 Not Found</h1>")

    def do_POST(self):
        print(f"[!] POST Request: {self.client_address[0]} -> {self.path}")
        user_agent = self.headers.get('User-Agent', 'Unknown')
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        parsed_data = urllib.parse.parse_qs(post_data)

        # Login İşlemleri
        if "wp-login.php" in self.path:
            username = parsed_data.get('log', [''])[0]
            password = parsed_data.get('pwd', [''])[0]
            
            log_attack(self.client_address[0], PORT, "HTTP-WP-Login", username, password, user_agent)
            
            # Eşik Kontrolü (Senin testin için 2, gerçekte 10)
            attempt_count = get_attempt_count(self.client_address[0])
            if attempt_count >= 2: # Burayı daha sonra 10 yaparsın
                self.send_response(302)
                self.send_header('Location', '/wp-admin/') 
                self.send_header('Set-Cookie', 'wordpress_logged_in=true; Path=/')
                self.end_headers()
            else:
                self._set_headers(200)
                with open(DECOY_LOGIN, "rb") as file:
                    self.wfile.write(file.read())

        # Malware (Shell) Yükleme İşlemleri
        elif "theme-editor.php" in self.path:
            injected_code = parsed_data.get('newcontent', [''])[0]
            payload_filename = f"malware_{uuid.uuid4().hex[:8]}.txt"
            payload_path = os.path.join(PAYLOAD_DIR, payload_filename)
            
            with open(payload_path, "w", encoding="utf-8") as f:
                f.write(injected_code)
                
            log_attack(self.client_address[0], PORT, "HTTP-WP-Shell-Upload", "theme-editor.php", f"Saved: {payload_filename}", user_agent)
            
            self._set_headers(200)
            self.wfile.write(b"<h1>File edited successfully.</h1> <a href='/wp-admin/theme-editor.php'>Go back</a>")

with socketserver.TCPServer(("0.0.0.0", PORT), HoneypotHTTPRequestHandler) as httpd:
    print(f"[*] MirageNet HTTP Sensor listening on Port: {PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")