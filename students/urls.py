"""
students/urls.py
----------------
URL configuration for the students app.
Namespace: 'students'
"""

from django.urls import path

from students import views

app_name = 'students'

urlpatterns = [
    # ── Student list & CRUD ───────────────────────────────────────────────────
    path('', views.student_list_view, name='student_list'),
    path('create/', views.student_create_view, name='student_create'),
    path('<int:pk>/', views.student_detail_view, name='student_detail'),
    path('<int:pk>/edit/', views.student_update_view, name='student_update'),

    # ── Student sub-resources ─────────────────────────────────────────────────
    path('<int:pk>/medical/', views.student_medical_update_view, name='student_medical_update'),
    path('<int:pk>/documents/upload/', views.student_document_upload_view, name='student_document_upload'),

    # ── Student status actions (POST only) ────────────────────────────────────
    path('<int:pk>/transfer/', views.student_transfer_view, name='student_transfer'),
    path('<int:pk>/withdraw/', views.student_withdraw_view, name='student_withdraw'),

    # ── Bulk promotion ────────────────────────────────────────────────────────
    path('promote/', views.student_promote_view, name='student_promote'),

    # ── Parents / Guardians ───────────────────────────────────────────────────
    path('parents/', views.parent_list_view, name='parent_list'),
    path('parents/create/', views.parent_create_view, name='parent_create'),
    path('parents/<int:pk>/edit/', views.parent_update_view, name='parent_update'),
    path('parents/<int:pk>/link/', views.parent_link_student_view, name='parent_link_student'),
]
