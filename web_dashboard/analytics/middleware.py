from django.shortcuts import redirect
from django.urls import reverse

class MirageControlCenterMiddleware:
    """
    Middleware to protect the secret control center and redirect all other 
    random traffic to the honeypot's WordPress login.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.secret_path = '/mirage-control-center/'

    def __call__(self, request):
        path = request.path
        
        # 1. Allow login and logout views without auth
        if path == self.secret_path or path == f"{self.secret_path}logout/":
            return self.get_response(request)

        # 2. If the user is trying to access anything inside the secret path
        if path.startswith(self.secret_path):
            if not request.session.get('mcc_authenticated'):
                return redirect(self.secret_path)
            return self.get_response(request)

        # 3. Allow static files (Django serving static in dev or handled by server)
        if path.startswith('/static/'):
            return self.get_response(request)

        # 4. EVERYTHING ELSE -> Redirect to the Honeypot's WP-Login
        # We redirect to the root of our own server's port 80/8080 or just a relative path if handled by same server.
        # Since they are on different ports usually, we can redirect to the known honeypot path.
        # If the user is on the dashboard port, we kick them to the honeypot entry.
        return redirect('http://127.0.0.1:8080/wp-login.php')
