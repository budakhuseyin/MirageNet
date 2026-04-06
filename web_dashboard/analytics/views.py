from django.shortcuts import render
from .models import AttackLog
from django.db.models import Count, Max
import json 

def dashboard_home(request):
    # Port'a göre grupluyoruz ki her session tek bir satır olarak gelsin
    recent_sessions = AttackLog.objects.values('session_id', 'ip_address', 'port').annotate(
        log_count=Count('id'),
        last_seen=Max('timestamp')
    ).order_by('-last_seen')[:20]

    context = {
        'recent_sessions': recent_sessions,
    }
    return render(request, 'analytics/dashboard.html', context)

def session_details(request, session_id):
    # Tıklanan session'a ait tüm logları kronolojik sırayla çekiyoruz
    logs = AttackLog.objects.filter(session_id=session_id).order_by('timestamp')
    
    return render(request, 'analytics/partials/terminal.html', {'logs': logs, 'session_id': session_id})



def session_list_partial(request):
    recent_sessions = AttackLog.objects.values('session_id', 'ip_address', 'port', 'latitude', 'longitude').annotate(
        log_count=Count('id'),
        last_seen=Max('timestamp')
    ).order_by('-last_seen')[:20]

    response = render(request, 'analytics/partials/session_list.html', {'recent_sessions': recent_sessions})
    
    # En son saldırıyı al ve tarayıcıya "yeni saldırı var" sinyali gönder
    if recent_sessions.exists():
        latest = recent_sessions[0]
        event_data = {
            "newAttack": {
                "lat": latest['latitude'],
                "lon": latest['longitude'],
                "ip": latest['ip_address']
            }
        }
        # HTMX-Trigger başlığı ile tarayıcıdaki JS'i tetikliyoruz
        response['HX-Trigger'] = json.dumps(event_data)
    
    return response


def map_view(request):
    """World Map partial — Leaflet.js ile yüklenir. Geçmiş saldırıları haritaya döker."""
    # Enlem ve boylamı geçerli olan (sıfır olmayan) son 500 saldırıyı çek.
    historical_data = list(AttackLog.objects.exclude(latitude=0).exclude(latitude__isnull=True).values(
        'ip_address', 'latitude', 'longitude'
    ).order_by('-id')[:500])
    
    context = {
        'historical_data_json': json.dumps(historical_data)
    }
    return render(request, 'analytics/partials/map_view.html', context)


def terminal_default_view(request):
    """Varsayılan boş terminal ekranını döner."""
    return render(request, 'analytics/partials/terminal_default.html')


def stats_view(request):
    return render(request, 'analytics/partials/coming_soon.html', {'module': 'Statistics'})


def forensics_view(request):
    return render(request, 'analytics/partials/coming_soon.html', {'module': 'Forensics'})


def settings_view(request):
    return render(request, 'analytics/partials/coming_soon.html', {'module': 'Settings'})