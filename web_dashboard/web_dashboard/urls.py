from django.urls import path, include
from analytics import views as analytics_views

urlpatterns = [
    # The new secret Mirage Control Center (MCC)
    path('mirage-control-center/', include([
        path('', analytics_views.login_view, name='login_view'),
        path('logout/', analytics_views.logout_view, name='logout_view'),
        path('dashboard/', include('analytics.urls')),
    ])),
]