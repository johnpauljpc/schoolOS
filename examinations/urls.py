from django.urls import path
from . import views

app_name = 'examinations'

urlpatterns = [
    # Grade Config
    path('grades/', views.grade_config_list_view, name='grade-list'),
    path('grades/add/', views.grade_config_create_view, name='grade-create'),
    path('grades/<int:pk>/edit/', views.grade_config_update_view, name='grade-update'),
    path('grades/<int:pk>/delete/', views.grade_config_delete_view, name='grade-delete'),
    # CA Entry
    path('ca/entry/', views.ca_entry_view, name='ca-entry-select'),
    path('ca/entry/', views.ca_entry_view, name='ca-entry'),
    # Exam Score Entry
    path('exam/entry/', views.exam_score_entry_view, name='exam-entry-select'),
    path('exam/entry/', views.exam_score_entry_view, name='exam-entry'),
    # Results
    path('results/', views.result_list_view, name='result-list'),
    path('results/compute/', views.compute_results_view, name='compute-results'),
    path('results/approve/', views.result_approve_view, name='result-approve'),
    path('results/publish/', views.result_publish_view, name='result-publish'),
    # Report Card
    path('results/report-card/<int:student_id>/', views.student_report_card_view, name='report-card'),
    path('results/report-card/<int:student_id>/pdf/', views.report_card_pdf_view, name='report-card-pdf'),
    path('results/transcript/<int:student_id>/pdf/', views.transcript_pdf_view, name='transcript-pdf'),
    # Timetables
    path('timetable/class/', views.class_timetable_view, name='class-timetable'),
    path('timetable/class/add/', views.class_timetable_create_view, name='class-timetable-create'),
    path('timetable/exam/', views.exam_timetable_list_view, name='exam-timetable'),
    path('timetable/exam/add/', views.exam_timetable_create_view, name='exam-timetable-create'),
]
