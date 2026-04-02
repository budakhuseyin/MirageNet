import http.server
import socketserver
import urllib.parse
import os
import sys

# shared klasöründeki database.py modülüne erişebilmek için yolu ekliyoruz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from shared.database import log_attack

PORT = 8080 
DECOY_PATH = "decoys/wp-login.html"

class HoneypotHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    
    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Server', 'Apache/2.4.41 (Ubuntu)') 
        self.end_headers()

    def do_GET(self):
        print(f"[!] GET Request: {self.client_address[0]} -> {self.path}")
        
        if "wp-login.php" in self.path:
            self._set_headers(200)
            with open(DECOY_PATH, "rb") as file:
                self.wfile.write(file.read())
        else:
            self._set_headers(404)
            self.wfile.write(b"<h1>404 Not Found</h1>")

    def do_POST(self):
        print(f"[!] POST Request: {self.client_address[0]} -> {self.path}")
        
        if "wp-login.php" in self.path:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Veriyi burada ayrıştırıp parsed_data değişkenine atıyoruz
            parsed_data = urllib.parse.parse_qs(post_data)
            
            # Değişkenleri güvenli bir şekilde çekiyoruz
            username = parsed_data.get('log', [''])[0]
            password = parsed_data.get('pwd', [''])[0]
            
            print("-" * 50)
            print("[***] TRAPPED! Captured Credentials:")
            print(f"Username      : {username}")
            print(f"Password      : {password}")
            print("-" * 50)
            
            # Veritabanına kaydediyoruz
            log_attack(
                ip_address=self.client_address[0],
                port=PORT,
                module="HTTP-WP-Login",
                username=username,
                password=password
            )
            
            self._set_headers(200)
            with open(DECOY_PATH, "rb") as file:
                self.wfile.write(file.read())

with socketserver.TCPServer(("0.0.0.0", PORT), HoneypotHTTPRequestHandler) as httpd:
    print(f"[*] MirageNet HTTP Sensor listening on Port: {PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")