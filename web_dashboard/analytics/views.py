from django.shortcuts import render
from .models import AttackLog
from django.db.models import Count, Max

def dashboard_home(request):
    # En son bağlanan oturumları (session_id) bulalım ve özetleyelim
    # Hangi session'dan kaç log gelmiş ve en son ne zaman aktifmiş?
    recent_sessions = AttackLog.objects.values('session_id', 'ip_address', 'module').annotate(
        log_count=Count('id'),
        last_seen=Max('timestamp')
    ).order_by('-last_seen')[:20]  # Son 20 aktif oturumu getir

    context = {
        'recent_sessions': recent_sessions,
    }
    
    return render(request, 'analytics/dashboard.html', context)