"""
academics/urls.py

URL patterns for the academics app.
Namespace: 'academics'
"""

from django.urls import path

from . import views

app_name = 'academics'

urlpatterns = [

    # ── Academic Sessions ────────────────────────────────────────────────────
    path('sessions/',                          views.session_list,        name='session_list'),
    path('sessions/create/',                   views.session_create,      name='session_create'),
    path('sessions/<int:pk>/edit/',            views.session_update,      name='session_update'),
    path('sessions/<int:pk>/set-current/',     views.session_set_current, name='session_set_current'),

    # ── Academic Terms ───────────────────────────────────────────────────────
    path('terms/',                             views.term_list,           name='term_list'),
    path('terms/create/',                      views.term_create,         name='term_create'),
    path('terms/<int:pk>/edit/',               views.term_update,         name='term_update'),
    path('terms/<int:pk>/set-current/',        views.term_set_current,    name='term_set_current'),

    # ── Departments ──────────────────────────────────────────────────────────
    path('departments/',                       views.department_list,     name='department_list'),
    path('departments/create/',                views.department_create,   name='department_create'),
    path('departments/<int:pk>/edit/',         views.department_update,   name='department_update'),

    # ── Class Levels ─────────────────────────────────────────────────────────
    path('class-levels/',                      views.class_level_list,    name='class_level_list'),
    path('class-levels/create/',               views.class_level_create,  name='class_level_create'),
    path('class-levels/<int:pk>/edit/',        views.class_level_update,  name='class_level_update'),

    # ── Class Arms ───────────────────────────────────────────────────────────
    path('class-arms/',                        views.class_arm_list,      name='class_arm_list'),
    path('class-arms/create/',                 views.class_arm_create,    name='class_arm_create'),
    path('class-arms/<int:pk>/edit/',          views.class_arm_update,    name='class_arm_update'),

    # ── Subjects ─────────────────────────────────────────────────────────────
    path('subjects/',                          views.subject_list,        name='subject_list'),
    path('subjects/create/',                   views.subject_create,      name='subject_create'),
    path('subjects/<int:pk>/edit/',            views.subject_update,      name='subject_update'),
    path('subjects/<int:pk>/delete/',          views.subject_delete,      name='subject_delete'),

    # ── Subject Assignments ──────────────────────────────────────────────────
    path(
        'subject-assignments/',
        views.subject_assignment_list,
        name='subject_assignment_list',
    ),
    path(
        'subject-assignments/create/',
        views.subject_assignment_create,
        name='subject_assignment_create',
    ),
    path(
        'subject-assignments/<int:pk>/delete/',
        views.subject_assignment_delete,
        name='subject_assignment_delete',
    ),

    # ── Class Teacher Assignments ────────────────────────────────────────────
    path(
        'class-teacher-assignments/',
        views.class_teacher_assignment_list,
        name='class_teacher_assignment_list',
    ),
    path(
        'class-teacher-assignments/create/',
        views.class_teacher_assignment_create,
        name='class_teacher_assignment_create',
    ),
]
