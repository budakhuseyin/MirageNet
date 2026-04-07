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
        last_seen=Max('timestamp'),
        last_id=Max('id')
    ).order_by('-last_seen')[:20]

    response = render(request, 'analytics/partials/session_list.html', {'recent_sessions': recent_sessions})

    # Sadece gerçekten YENİ bir saldırı varsa radar eventi gönder
    if recent_sessions.exists():
        latest = recent_sessions[0]
        lat = latest.get('latitude') or 0.0
        lon = latest.get('longitude') or 0.0
        last_id = latest.get('last_id', 0)

        # Client'ın gönderdiği son bilinen ID ile karşılaştır
        client_last_id = int(request.GET.get('last_id', 0))

        if last_id > client_last_id and lat != 0.0 and lon != 0.0:
            event_data = {
                "newAttack": {
                    "id": last_id,
                    "lat": lat,
                    "lon": lon,
                    "ip": latest['ip_address']
                }
            }
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


from datetime import timedelta
from django.utils import timezone
from django.db.models.functions import TruncHour

def stats_view(request):
    """Genel Durum, Çizelgeler ve Karmaşıklık İstatistikleri"""
    
    # 1. Genel Durum Paneli
    total_events = AttackLog.objects.count()
    unique_attackers = AttackLog.objects.values('ip_address').distinct().count()
    
    total_sessions = AttackLog.objects.values('session_id').distinct().count()
    # Başarılı sayılanlar: SSH-Command modülüne ulaşabilenler (içeri girenler)
    successful_sessions = AttackLog.objects.filter(module='SSH-Command').values('session_id').distinct().count()
    success_ratio = round((successful_sessions / total_sessions * 100)) if total_sessions > 0 else 0
    
    first_log = AttackLog.objects.order_by('timestamp').first()
    uptime_str = "0h 0m"
    if first_log:
        uptime_delta = timezone.now() - first_log.timestamp
        days, rem = divmod(uptime_delta.total_seconds(), 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m" if days > 0 else f"{int(hours)}h {int(minutes)}m"

    # 2. Saldırı Zaman Çizelgesi (Son 24 Saat)
    last_24h = timezone.now() - timedelta(hours=24)
    timeline_data = AttackLog.objects.filter(timestamp__gte=last_24h) \
        .annotate(hour=TruncHour('timestamp')) \
        .values('hour') \
        .annotate(count=Count('id')) \
        .order_by('hour')
    
    timeline_labels = [item['hour'].strftime("%H:00") for item in timeline_data]
    timeline_counts = [item['count'] for item in timeline_data]

    # 3. Port & Modül Dağılımı
    ports_data = list(AttackLog.objects.values('port').annotate(count=Count('id')).order_by('-count'))
    modules_data = list(AttackLog.objects.values('module').annotate(count=Count('id')).order_by('-count'))
    
    # 4. En Çok Denenen Şifreler ve Kullanıcı Adları
    top_users = list(AttackLog.objects.exclude(username__in=['N/A', '-']).values('username').annotate(count=Count('id')).order_by('-count')[:5])
    top_passwords = list(AttackLog.objects.exclude(password__in=['N/A', '-', 'Scanning', 'Attempted download']).values('password').annotate(count=Count('id')).order_by('-count')[:5])

    # 5. Coğrafi Dağılım
    top_countries = list(AttackLog.objects.exclude(country_code='??').exclude(country_code='XX').values('country_code').annotate(count=Count('id')).order_by('-count')[:7])

    # 6. Saldırgan Karmaşıklığı (Complexity Score)
    session_cmd_counts = AttackLog.objects.filter(module='SSH-Command').values('session_id').annotate(cmd_count=Count('id'))
    high_complexity = sum(1 for s in session_cmd_counts if s['cmd_count'] > 5)
    med_complexity = sum(1 for s in session_cmd_counts if 2 <= s['cmd_count'] <= 5)
    low_complexity = total_sessions - (high_complexity + med_complexity)

    context = {
        'total_events': total_events,
        'unique_attackers': unique_attackers,
        'success_ratio': success_ratio,
        'uptime_str': uptime_str,
        'chart_data_json': {
            'timeline': {'labels': timeline_labels, 'data': timeline_counts},
            'ports': {'labels': [str(p['port']) for p in ports_data], 'data': [p['count'] for p in ports_data]},
            'modules': {'labels': [m['module'] for m in modules_data], 'data': [m['count'] for m in modules_data]},
            'top_users': {'labels': [u['username'] for u in top_users], 'data': [u['count'] for u in top_users]},
            'top_passwords': {'labels': [p['password'] for p in top_passwords], 'data': [p['count'] for p in top_passwords]},
            'top_countries': {'labels': [c['country_code'] for c in top_countries], 'data': [c['count'] for c in top_countries]},
            'complexity': {'labels': ['Low', 'Medium', 'High'], 'data': [low_complexity, med_complexity, high_complexity]}
        }
    }
    
    return render(request, 'analytics/partials/stats_view.html', context)


def forensics_view(request):
    return render(request, 'analytics/partials/coming_soon.html', {'module': 'Forensics'})


def settings_view(request):
    return render(request, 'analytics/partials/coming_soon.html', {'module': 'Settings'})