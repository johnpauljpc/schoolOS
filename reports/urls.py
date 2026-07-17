from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.report_index, name='index'),
    path('students/', views.student_report, name='students'),
    path('staff/', views.staff_report, name='staff'),
    path('academics/', views.academic_performance_report, name='academics'),
    path('admissions/', views.admissions_report, name='admissions'),
    path('finance/', views.finance_report, name='finance'),
    path('export/students/excel/', views.export_students_excel, name='export-students-excel'),
    path('export/finance/excel/', views.export_finance_excel, name='export-finance-excel'),
]
