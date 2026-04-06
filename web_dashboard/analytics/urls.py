from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    # HTMX bu adrese istek atıp terminal verilerini çekecek
    path('session/<str:session_id>/', views.session_details, name='session_details'), 
]