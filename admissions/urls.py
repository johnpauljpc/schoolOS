"""
admissions/urls.py

URL configuration for the admissions app.
Namespace: 'admissions'

Public routes (no login required):
  /admissions/apply/          → application_form_view
  /admissions/apply/success/  → application_success_view

Staff routes (login required):
  /admissions/applicants/                     → applicant_list_view
  /admissions/applicants/<pk>/               → applicant_detail_view
  /admissions/applicants/<pk>/review/        → applicant_review_view
  /admissions/applicants/<pk>/admit/         → admit_applicant_view
  /admissions/list/                           → admission_list_view
  /admissions/<pk>/letter/pdf/               → admission_letter_pdf_view
"""

from django.urls import path
from . import views

app_name = 'admissions'

urlpatterns = [
    # ── Public ────────────────────────────────────────────────────────────────
    path('apply/', views.application_form_view, name='apply'),
    path('apply/success/', views.application_success_view, name='application_success'),

    # ── Applicant management ─────────────────────────────────────────────────
    path('applicants/', views.applicant_list_view, name='applicant_list'),
    path('applicants/<int:pk>/', views.applicant_detail_view, name='applicant_detail'),
    path('applicants/<int:pk>/review/', views.applicant_review_view, name='applicant_review'),
    path('applicants/<int:pk>/admit/', views.admit_applicant_view, name='admit_applicant'),

    # ── Admission records ────────────────────────────────────────────────────
    path('list/', views.admission_list_view, name='admission_list'),
    path('<int:pk>/letter/pdf/', views.admission_letter_pdf_view, name='admission_letter_pdf'),
]
