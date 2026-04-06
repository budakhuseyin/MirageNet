import http.server
import socketserver
import urllib.parse
import os
import sys
import uuid
import http.cookies

# Shared modülüne ve klasörlere erişim için yol ayarları
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '../../'))
sys.path.append(PROJECT_ROOT)

from shared.database import log_attack, get_attempt_count

PORT = 8080 

# DOSYA YOLLARINI SABİTLEDİK
DECOY_DIR = os.path.join(CURRENT_DIR, "decoys")
DECOY_LOGIN = os.path.join(DECOY_DIR, "wp-login.html")
DECOY_DASHBOARD = os.path.join(DECOY_DIR, "wp-dashboard.html")
DECOY_EDITOR = os.path.join(DECOY_DIR, "wp-theme-editor.html")

PAYLOAD_DIR = os.path.join(PROJECT_ROOT, "data", "payloads")
if not os.path.exists(PAYLOAD_DIR):
    os.makedirs(PAYLOAD_DIR)

class HoneypotHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    
    def get_or_create_session(self):
        cookie_header = self.headers.get('Cookie', '')
        cookie = http.cookies.SimpleCookie(cookie_header)
        if 'mnet_sid' in cookie:
            return cookie['mnet_sid'].value
        return str(uuid.uuid4())[:8]

    def _set_headers(self, status_code=200, content_type='text/html; charset=utf-8', session_id=None):
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.send_header('Server', 'Apache/2.4.41 (Ubuntu)') 
        if session_id:
            self.send_header('Set-Cookie', f'mnet_sid={session_id}; Path=/; HttpOnly')
        self.end_headers()

    def do_GET(self):
        session_id = self.get_or_create_session()
        print(f"[!] GET Request: {self.client_address[0]} [SID: {session_id}] -> {self.path}")
        user_agent = self.headers.get('User-Agent', 'Unknown')

        if "wp-login.php" in self.path:
            self._set_headers(200, session_id=session_id)
            with open(DECOY_LOGIN, "rb") as file:
                self.wfile.write(file.read())
            # GET İsteklerini de logluyoruz (Sadece wp-login için)
            log_attack(
                ip_address=self.client_address[0], port=80, module="HTTP-GET",
                username="N/A", password="N/A", user_agent=user_agent, session_id=session_id,
                event_data=f"GET {self.path}", response_data="HTTP 200 OK - Served wp-login page", country_code="??"
            )

        elif ".env" in self.path:
            fake_env = "DB_HOST=localhost\nDB_USER=root\nDB_PASS=S3cur3P@ssw0rd!\nAWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
            # 11 Parametreli loglama
            log_attack(
                ip_address=self.client_address[0], port=80, module="HTTP-DOT-ENV", 
                username="N/A", password="Attempted download", user_agent=user_agent, session_id=session_id,
                event_data=f"GET {self.path}", response_data="HTTP 200 OK - Served Fake .env File", country_code="??"
            )
            self._set_headers(200, 'text/plain', session_id=session_id)
            self.wfile.write(fake_env.encode())

        elif "phpmyadmin" in self.path.lower():
            # 11 Parametreli loglama
            log_attack(
                ip_address=self.client_address[0], port=80, module="HTTP-PHPMYADMIN", 
                username="N/A", password="Scanning", user_agent=user_agent, session_id=session_id,
                event_data=f"GET {self.path}", response_data="HTTP 403 Forbidden", country_code="??"
            )
            self._set_headers(403, session_id=session_id)
            self.wfile.write(b"<h1>403 Forbidden: Access Denied</h1>")

        elif self.path == "/wp-admin/" or self.path == "/wp-admin/index.php":
            self._set_headers(200, session_id=session_id)
            with open(DECOY_DASHBOARD, "rb") as file:
                self.wfile.write(file.read())
            log_attack(
                ip_address=self.client_address[0], port=80, module="HTTP-GET",
                username="N/A", password="N/A", user_agent=user_agent, session_id=session_id,
                event_data=f"GET {self.path}", response_data="HTTP 200 OK - Served Admin Dashboard", country_code="??"
            )

        elif "theme-editor.php" in self.path:
            self._set_headers(200, session_id=session_id)
            with open(DECOY_EDITOR, "rb") as file:
                self.wfile.write(file.read())
            log_attack(
                ip_address=self.client_address[0], port=80, module="HTTP-GET",
                username="N/A", password="N/A", user_agent=user_agent, session_id=session_id,
                event_data=f"GET {self.path}", response_data="HTTP 200 OK - Served Theme Editor", country_code="??"
            )

        else:
            self._set_headers(404, session_id=session_id)
            self.wfile.write(b"<h1>404 Not Found</h1>")

    def do_POST(self):
        session_id = self.get_or_create_session()
        print(f"[!] POST Request: {self.client_address[0]} [SID: {session_id}] -> {self.path}")
        user_agent = self.headers.get('User-Agent', 'Unknown')
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        parsed_data = urllib.parse.parse_qs(post_data)

        if "wp-login.php" in self.path:
            username = parsed_data.get('log', [''])[0]
            password = parsed_data.get('pwd', [''])[0]
            
            attempt_count = get_attempt_count(self.client_address[0], session_id, "HTTP-WP-Login")     
            
            if attempt_count >= 2: 
                # Başarılı Giriş Logu
                log_attack(
                    ip_address=self.client_address[0], port=80, module="HTTP-WP-Login", 
                    username=username, password=password, user_agent=user_agent, session_id=session_id,
                    event_data=f"POST /wp-login.php (User: {username}, Pass: {password})", 
                    response_data="HTTP 302 Redirect -> /wp-admin/", country_code="??"
                )
                self.send_response(302)
                self.send_header('Location', '/wp-admin/') 
                self.send_header('Set-Cookie', f'mnet_sid={session_id}; Path=/; HttpOnly')
                self.send_header('Set-Cookie', 'wordpress_logged_in=true; Path=/')
                self.end_headers()
            else:
                # Başarısız Giriş Logu
                log_attack(
                    ip_address=self.client_address[0], port=80, module="HTTP-WP-Login", 
                    username=username, password=password, user_agent=user_agent, session_id=session_id,
                    event_data=f"POST /wp-login.php (User: {username}, Pass: {password})", 
                    response_data="HTTP 200 OK - Invalid Credentials Page", country_code="??"
                )
                self._set_headers(200, session_id=session_id)
                with open(DECOY_LOGIN, "rb") as file:
                    self.wfile.write(file.read())

        elif "theme-editor.php" in self.path:
            injected_code = parsed_data.get('newcontent', [''])[0]
            payload_filename = f"malware_{uuid.uuid4().hex[:8]}.txt"
            payload_path = os.path.join(PAYLOAD_DIR, payload_filename)
            with open(payload_path, "w", encoding="utf-8") as f:
                f.write(injected_code)
                
            # Shell Upload Logu
            log_attack(
                ip_address=self.client_address[0], port=80, module="HTTP-WP-Shell-Upload", 
                username="theme-editor.php", password=f"Saved: {payload_filename}", user_agent=user_agent, session_id=session_id,
                event_data=f"POST /wp-admin/theme-editor.php (File Write)", 
                response_data=f"HTTP 200 OK - File edited successfully. Payload saved as: {payload_filename}", country_code="??"
            )
            self._set_headers(200, session_id=session_id)
            self.wfile.write(b"<h1>File edited successfully.</h1> <a href='/wp-admin/theme-editor.php'>Go back</a>")

with socketserver.TCPServer(("0.0.0.0", PORT), HoneypotHTTPRequestHandler) as httpd:
    print(f"[*] MirageNet HTTP Sensor listening on Port: {PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")