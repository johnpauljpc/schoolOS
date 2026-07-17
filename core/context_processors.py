from django.conf import settings
from communication.models import Notification


def school_info(request):
    """Inject school info into every template context."""
    return {
        'SCHOOL_NAME': getattr(settings, 'SCHOOL_NAME', 'SchoolOS Academy'),
        'SCHOOL_TAGLINE': getattr(settings, 'SCHOOL_TAGLINE', 'Excellence in Education'),
        'SCHOOL_ADDRESS': getattr(settings, 'SCHOOL_ADDRESS', ''),
        'SCHOOL_PHONE': getattr(settings, 'SCHOOL_PHONE', ''),
        'SCHOOL_EMAIL': getattr(settings, 'SCHOOL_EMAIL', ''),
    }


def notifications(request):
    """Inject unread notification count for authenticated users."""
    unread_count = 0
    recent_notifications = []
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
        recent_notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
    return {
        'unread_notification_count': unread_count,
        'recent_notifications': recent_notifications,
    }
