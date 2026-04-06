from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    # HTMX bu adrese istek atıp terminal verilerini çekecek
    path('session/<str:session_id>/', views.session_details, name='session_details'), 
    # HTMX bu adrese istek atıp sol paneli güncelleyecek
    path('sessions-poll/', views.session_list_partial, name='session_list_partial'),
]