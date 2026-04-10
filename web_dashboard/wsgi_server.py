import os
import sys
from waitress import serve
from django.core.wsgi import get_wsgi_application

# Django ayarlarını yükle
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_dashboard.settings')

# Proje kök dizinini yol listesine ekle (import hatalarını önlemek için)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    application = get_wsgi_application()
    print("[*] Waitress WSGI Server starting on http://127.0.0.1:8000")
    serve(application, host='127.0.0.1', port=8000, threads=6) # 6 thread bir honeypot dashboard için idealdir
except Exception as e:
    print(f"[!] Waitress failed to start: {e}")
    sys.exit(1)
