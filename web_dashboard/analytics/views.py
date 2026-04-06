from django.shortcuts import render
from .models import AttackLog
from django.db.models import Count, Max

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