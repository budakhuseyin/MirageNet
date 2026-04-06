from django.contrib import admin
from django.urls import path, include # include'u eklemeyi unutma

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('analytics.urls')), # Ana dizine girince analytics çalışsın
]