import json
import hashlib
from datetime import timedelta
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Count, Max
from django.db.models.functions import TruncHour, TruncMinute, TruncDay
from django.http import JsonResponse
from django.core import serializers
from .models import AttackLog

def login_view(request):
    """Simple hardcoded login for Mirage Control Center."""
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        
        # Hardcoded logic as requested by user
        if u == 'mirage_admin' and p == 'mirage2172':
            request.session['mcc_authenticated'] = True
            return redirect('dashboard_home')
        else:
            return render(request, 'analytics/login.html', {'error': 'Geçersiz kullanıcı adı veya şifre!'})
            
    return render(request, 'analytics/login.html')

def logout_view(request):
    """Logs out the user from MCC."""
    if 'mcc_authenticated' in request.session:
        del request.session['mcc_authenticated']
    return redirect('login_view')

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
    # Eğer Forensics tabı açıksa, o oturum için adli analizi aç
    if request.session.get('active_tab') == 'forensics':
        return forensic_report_view(request, session_id)

    # Tıklanan session'a ait tüm logları kronolojik sırayla çekiyoruz (Canlı Terminal Modu)
    logs = AttackLog.objects.filter(session_id=session_id).order_by('timestamp')
    return render(request, 'analytics/partials/terminal.html', {'logs': logs, 'session_id': session_id})

def session_list_partial(request):
    recent_sessions = list(AttackLog.objects.values('session_id', 'ip_address', 'port', 'latitude', 'longitude').annotate(
        log_count=Count('id'),
        last_seen=Max('timestamp'),
        last_id=Max('id')
    ).order_by('-last_seen')[:20])

    now = timezone.now()
    for s in recent_sessions:
        diff = now - s['last_seen']
        if diff < timedelta(minutes=3):
            s['status'] = 'active'
        elif diff < timedelta(minutes=10):
            s['status'] = 'recent'
        else:
            s['status'] = 'idle'

    response = render(request, 'analytics/partials/session_list.html', {'recent_sessions': recent_sessions})

    # Sadece gerçekten YENİ bir saldırı varsa radar eventi gönder
    if recent_sessions:
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
    request.session['active_tab'] = 'map'
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
    request.session['active_tab'] = 'terminal'
    return render(request, 'analytics/partials/terminal_default.html')


def stats_view(request):
    """Genel Durum, Çizelgeler ve Karmaşıklık İstatistikleri"""
    request.session['active_tab'] = 'stats'
    
    # Zaman Aralığı Filtresi
    time_range = request.GET.get('range', '24h')
    now = timezone.now()
    start_time = None
    trunc_func = TruncHour
    date_format = "%H:00"

    if time_range == '1h':
        start_time = now - timedelta(hours=1)
        trunc_func = TruncMinute
        date_format = "%H:%M"
    elif time_range == '3h':
        start_time = now - timedelta(hours=3)
        trunc_func = TruncMinute
        date_format = "%H:%M"
    elif time_range == '6h':
        start_time = now - timedelta(hours=6)
        trunc_func = TruncHour
        date_format = "%H:00"
    elif time_range == '12h':
        start_time = now - timedelta(hours=12)
        trunc_func = TruncHour
        date_format = "%H:00"
    elif time_range == '7d':
        start_time = now - timedelta(days=7)
        trunc_func = TruncDay
        date_format = "%Y-%m-%d"
    elif time_range == '30d':
        start_time = now - timedelta(days=30)
        trunc_func = TruncDay
        date_format = "%Y-%m-%d"
    elif time_range == 'all':
        start_time = None
        trunc_func = TruncDay
        date_format = "%Y-%m-%d"
    else: # Default 24h
        start_time = now - timedelta(hours=24)
        trunc_func = TruncHour
        date_format = "%H:00"
        time_range = '24h'

    # Ortak filtrelemesi
    base_qs = AttackLog.objects.all()
    if start_time:
        base_qs = base_qs.filter(timestamp__gte=start_time)

    # 1. Genel Durum Paneli
    total_events = base_qs.count()
    unique_attackers = base_qs.values('ip_address').distinct().count()
    
    total_sessions = base_qs.values('session_id').distinct().count()
    # Başarılı sayılanlar: SSH-Command modülüne ulaşabilenler (içeri girenler)
    successful_sessions = base_qs.filter(module='SSH-Command').values('session_id').distinct().count()
    success_ratio = round((successful_sessions / total_sessions * 100)) if total_sessions > 0 else 0
    
    # Uptime statiktir, sistem başladığından beri geçerlidir
    first_log = AttackLog.objects.order_by('timestamp').first()
    uptime_str = "0h 0m"
    if first_log:
        uptime_delta = timezone.now() - first_log.timestamp
        days, rem = divmod(uptime_delta.total_seconds(), 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m" if days > 0 else f"{int(hours)}h {int(minutes)}m"

    # 2. Saldırı Zaman Çizelgesi (Dinamik Gruplama)
    timeline_data = base_qs.annotate(time_unit=trunc_func('timestamp')) \
        .values('time_unit') \
        .annotate(count=Count('id')) \
        .order_by('time_unit')
    
    timeline_labels = [item['time_unit'].strftime(date_format) for item in timeline_data]
    timeline_counts = [item['count'] for item in timeline_data]

    # 3. Port & Modül Dağılımı
    ports_data = list(base_qs.values('port').annotate(count=Count('id')).order_by('-count'))
    modules_data = list(base_qs.values('module').annotate(count=Count('id')).order_by('-count'))
    
    # 4. En Çok Denenen Şifreler ve Kullanıcı Adları
    top_users = list(base_qs.exclude(username__in=['N/A', '-']).values('username').annotate(count=Count('id')).order_by('-count')[:5])
    top_passwords = list(base_qs.exclude(password__in=['N/A', '-', 'Scanning', 'Attempted download']).values('password').annotate(count=Count('id')).order_by('-count')[:5])

    # 5. Coğrafi Dağılım
    top_countries = list(base_qs.exclude(country_code='??').exclude(country_code='XX').values('country_code').annotate(count=Count('id')).order_by('-count')[:7])

    # 6. Saldırgan Karmaşıklığı (Complexity Score)
    session_cmd_counts = base_qs.filter(module='SSH-Command').values('session_id').annotate(cmd_count=Count('id'))
    high_complexity = sum(1 for s in session_cmd_counts if s['cmd_count'] > 5)
    med_complexity = sum(1 for s in session_cmd_counts if 2 <= s['cmd_count'] <= 5)
    low_complexity = total_sessions - (high_complexity + med_complexity)

    context = {
        'total_events': total_events,
        'unique_attackers': unique_attackers,
        'success_ratio': success_ratio,
        'uptime_str': uptime_str,
        'selected_range': time_range,
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
    request.session['active_tab'] = 'forensics'
    return render(request, 'analytics/partials/forensics_default.html')

def forensic_report_view(request, session_id):
    logs = AttackLog.objects.filter(session_id=session_id).order_by('timestamp')
    if not logs.exists():
        return render(request, 'analytics/partials/coming_soon.html', {'module': 'Session Not Found'})
    
    first_log = logs.first()
    ip_address = first_log.ip_address
    
    # Otomatik Tehdit Davranışı Sınıflandırması
    behavior = "Discovery & Reconnaissance"
    payloads = []
    dangerous_command_ids = []
    has_brute = logs.filter(module='SSH-Login').exists()
    
    for l in logs:
        data = (l.event_data or '').strip()
        data_lower = data.lower()
        if 'wget ' in data_lower or 'curl ' in data_lower or 'ftp ' in data_lower:
            behavior = "Malware Deployment"
            parts = data.split()
            url = next((p for p in parts if p.startswith('http') or '.sh' in p or '.bin' in p or '.elf' in p or '.txt' in p), 'unknown_payload')
            pseudo_hash = hashlib.sha256(url.encode()).hexdigest()
            payloads.append({'cmd': data, 'url': url, 'hash': pseudo_hash})
            dangerous_command_ids.append(l.id)
        elif any(kw in data_lower for kw in ['cat /etc/', 'sudo', 'passwd', 'shadow', 'chmod', 'rm -rf']):
            if behavior != "Malware Deployment":
                behavior = "Privilege Escalation & Exfiltration"
            dangerous_command_ids.append(l.id)
            
    if has_brute and behavior == "Discovery & Reconnaissance":
        behavior = "Brute Force Attempt"

    context = {
        'session_id': session_id,
        'ip_address': ip_address,
        'logs': logs,
        'behavior': behavior,
        'payloads': payloads,
        'dangerous_command_ids': dangerous_command_ids,
        'reputation': 'Critical Malicious / Botnet Node' if payloads else 'Suspicious / Scanner',
        'signature': 'Custom Script / Bot' if not first_log.user_agent or 'python' in first_log.user_agent.lower() else 'OpenSSH / Standard Scanner'
    }
    return render(request, 'analytics/partials/forensics.html', context)


def export_session_json(request, session_id):
    logs = AttackLog.objects.filter(session_id=session_id)
    data = list(logs.values())
    response = JsonResponse(data, safe=False, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename=miragenet_report_{session_id}.json'
    return response

def export_session_pdf(request, session_id):
    # Bu view, forensic_report_view ile aynı mantığı kullanır ama modal/partial yerine tam sayfa döner.
    logs = AttackLog.objects.filter(session_id=session_id).order_by('timestamp')
    if not logs.exists():
        return render(request, 'analytics/partials/coming_soon.html', {'module': 'Session Not Found'})
    
    first_log = logs.first()
    ip_address = first_log.ip_address
    
    # Logic duplication from forensic_report_view (can be refactored, but kept simple for now)
    behavior = "Discovery & Reconnaissance"
    payloads = []
    dangerous_command_ids = []
    has_brute = logs.filter(module='SSH-Login').exists()
    
    for l in logs:
        data = (l.event_data or '').strip()
        data_lower = data.lower()
        if 'wget ' in data_lower or 'curl ' in data_lower or 'ftp ' in data_lower:
            behavior = "Malware Deployment"
            parts = data.split()
            url = next((p for p in parts if p.startswith('http') or '.sh' in p or '.bin' in p or '.elf' in p or '.txt' in p), 'unknown_payload')
            pseudo_hash = hashlib.sha256(url.encode()).hexdigest()
            payloads.append({'cmd': data, 'url': url, 'hash': pseudo_hash})
            dangerous_command_ids.append(l.id)
        elif any(kw in data_lower for kw in ['cat /etc/', 'sudo', 'passwd', 'shadow', 'chmod', 'rm -rf']):
            if behavior != "Malware Deployment":
                behavior = "Privilege Escalation & Exfiltration"
            dangerous_command_ids.append(l.id)
    if has_brute and behavior == "Discovery & Reconnaissance":
        behavior = "Brute Force Attempt"

    context = {
        'session_id': session_id,
        'ip_address': ip_address,
        'logs': logs,
        'behavior': behavior,
        'payloads': payloads,
        'dangerous_command_ids': dangerous_command_ids,
        'reputation': 'Critical Malicious / Botnet Node' if payloads else 'Suspicious / Scanner',
        'signature': 'Custom Script / Bot' if not first_log.user_agent or 'python' in first_log.user_agent.lower() else 'OpenSSH / Standard Scanner'
    }
    return render(request, 'analytics/forensic_report_full.html', context)



def settings_view(request):
    request.session['active_tab'] = 'settings'
    return render(request, 'analytics/partials/coming_soon.html', {'module': 'Settings'})
