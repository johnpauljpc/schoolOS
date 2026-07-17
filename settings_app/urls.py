from django.urls import path
from . import views

app_name = 'settings_app'

urlpatterns = [
    path('', views.settings_index, name='index'),
    path('audit-logs/', views.audit_logs, name='audit-logs'),
    path('login-activity/', views.login_activity, name='login-activity'),
]
