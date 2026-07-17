from django.urls import path
from . import views

app_name = 'staff'

urlpatterns = [
    path('', views.staff_list, name='list'),
    path('teachers/', views.teacher_list, name='teacher-list'),
    path('add/', views.staff_create, name='create'),
    path('<int:pk>/', views.staff_detail, name='detail'),
    path('<int:pk>/edit/', views.staff_update, name='update'),
    path('<int:pk>/toggle/', views.staff_toggle_active, name='toggle-active'),
    path('<int:staff_pk>/qualification/add/', views.qualification_add, name='qualification-add'),
    path('qualification/<int:pk>/delete/', views.qualification_delete, name='qualification-delete'),
]
