import http.server
import socketserver
import urllib.parse
import os

# Using 8080 for local testing to avoid permission errors. 
# We will change this to 80 when deploying to a live server (VPS).
PORT = 8080 
DECOY_PATH = "decoys/wp-login.html"

class HoneypotHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    
    # Helper function to set HTTP response headers
    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Server', 'Apache/2.4.41 (Ubuntu)') # Fake server info to deceive bots
        self.end_headers()

    # When a bot wants to view the page (GET)
    def do_GET(self):
        print(f"[!] GET Request: {self.client_address[0]} -> {self.path}")
        
        # If the bot is looking for the wp-login.php page, read and send our HTML file
        if "wp-login.php" in self.path:
            self._set_headers(200)
            with open(DECOY_PATH, "rb") as file:
                self.wfile.write(file.read())
        else:
            # Return 404 if it's looking for any other random directory
            self._set_headers(404)
            self.wfile.write(b"<h1>404 Not Found</h1>")

    # When the bot fills the form and clicks 'Log In' (POST)
    def do_POST(self):
        print(f"[!] POST Request: {self.client_address[0]} -> {self.path}")
        
        if "wp-login.php" in self.path:
            # Get the length of the data sent by the bot (username and password)
            content_length = int(self.headers['Content-Length'])
            
            # Read the data and convert it to a string (e.g., log=admin&pwd=123456&wp-submit=Log+In)
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Parse the complex HTTP data into a dictionary structure
            parsed_data = urllib.parse.parse_qs(post_data)
            
            # Print the credentials! (We will send this to the database later)
            print("-" * 50)
            print("[***] TRAPPED! Captured Credentials:")
            print(f"Username      : {parsed_data.get('log', [''])[0]}")
            print(f"Password      : {parsed_data.get('pwd', [''])[0]}")
            print("-" * 50)
            
            # Show the login page again so the bot doesn't get suspicious (as if the password was wrong)
            self._set_headers(200)
            with open(DECOY_PATH, "rb") as file:
                self.wfile.write(file.read())

# Start the server
with socketserver.TCPServer(("0.0.0.0", PORT), HoneypotHTTPRequestHandler) as httpd:
    print(f"[*] MirageNet HTTP Sensor listening on Port: {PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")