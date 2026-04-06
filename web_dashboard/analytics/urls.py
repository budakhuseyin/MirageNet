from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    # HTMX session terminal
    path('session/<str:session_id>/', views.session_details, name='session_details'),
    # HTMX sol panel polling
    path('sessions-poll/', views.session_list_partial, name='session_list_partial'),
    # Nav bar view routes
    path('view/map/', views.map_view, name='map_view'),
    path('view/terminal/', views.terminal_default_view, name='terminal_default_view'),
    path('view/stats/', views.stats_view, name='stats_view'),
    path('view/forensics/', views.forensics_view, name='forensics_view'),
    path('view/settings/', views.settings_view, name='settings_view'),
]