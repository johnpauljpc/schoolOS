"""
accounts/urls.py
----------------
URL configuration for the accounts app.
Namespace: 'accounts'
"""

from django.urls import path
from accounts import views

app_name = 'accounts'

urlpatterns = [
    # ── Authentication ─────────────────────────────────────────────────────────
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── Profile ────────────────────────────────────────────────────────────────
    path('profile/',        views.profile_view,        name='profile'),
    path('profile/update/', views.profile_update_view, name='profile_update'),

    # ── Password Management ────────────────────────────────────────────────────
    path('password/change/',                         views.change_password_view,         name='change_password'),
    path('password-reset/',                          views.password_reset_request_view,  name='password_reset_request'),
    path('password-reset/confirm/<str:token>/',      views.password_reset_confirm_view,  name='password_reset_confirm'),

    # ── Email Verification ────────────────────────────────────────────────────
    path('email/verify/<str:token>/', views.email_verify_view, name='email_verify'),

    # ── Admin: User Management ────────────────────────────────────────────────
    path('users/',                          views.user_list_view,         name='user_list'),
    path('users/create/',                   views.user_create_view,       name='user_create'),
    path('users/<int:pk>/update/',          views.user_update_view,       name='user_update'),
    path('users/<int:pk>/toggle-active/',   views.user_toggle_active_view, name='user_toggle_active'),
]
