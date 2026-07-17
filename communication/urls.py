from django.urls import path
from . import views

app_name = 'communication'

urlpatterns = [
    # Announcements
    path('announcements/', views.announcement_list, name='announcements'),
    path('announcements/manage/', views.announcement_manage, name='manage'),
    path('announcements/new/', views.announcement_create, name='announcement-create'),
    path('announcements/<int:pk>/edit/', views.announcement_update, name='announcement-update'),
    path('announcements/<int:pk>/delete/', views.announcement_delete, name='announcement-delete'),
    path('announcements/<int:pk>/publish/', views.announcement_publish, name='announcement-publish'),
    # Notifications
    path('notifications/', views.notification_list, name='notifications'),
    path('notifications/<int:pk>/read/', views.notification_mark_read, name='notification-read'),
    path('notifications/mark-all-read/', views.notification_mark_all_read, name='notifications-mark-all'),
    # Messages
    path('messages/inbox/', views.inbox, name='inbox'),
    path('messages/sent/', views.sent_messages, name='sent'),
    path('messages/compose/', views.message_compose, name='compose'),
    path('messages/<int:pk>/', views.message_detail, name='message-detail'),
    path('messages/<int:pk>/reply/', views.message_reply, name='message-reply'),
]
