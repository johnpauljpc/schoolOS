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


def user_permissions(request):
    """
    Inject clean boolean permission flags into every template context.

    These replace fragile `role in '...'|split:','` checks in templates.
    Usage in templates:  {% if is_admin %} ... {% endif %}
    """
    if not request.user.is_authenticated:
        return {
            'is_admin': False,
            'is_senior_staff': False,
            'is_any_staff': False,
            'is_admission_staff': False,
            'is_finance_staff': False,
            'is_teacher': False,
            'is_student': False,
            'is_parent': False,
        }

    role = getattr(request.user, 'role', '')
    su = request.user.is_superuser

    return {
        # System administrators only
        'is_admin': su or role in ('SUPER_ADMIN', 'ICT_ADMIN'),

        # Principal + VP + admins — can manage academic settings, approve results
        'is_senior_staff': su or role in ('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'VICE_PRINCIPAL'),

        # Any staff member (everyone except students and parents)
        'is_any_staff': su or role in (
            'SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'VICE_PRINCIPAL',
            'ADMISSION_OFFICER', 'ACCOUNTANT', 'TEACHER', 'CLASS_TEACHER',
        ),

        # Can manage admissions
        'is_admission_staff': su or role in (
            'SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'VICE_PRINCIPAL', 'ADMISSION_OFFICER',
        ),

        # Can view/manage finance
        'is_finance_staff': su or role in (
            'SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT',
        ),

        # Teaching roles
        'is_teacher': su or role in ('TEACHER', 'CLASS_TEACHER'),

        # Student portal
        'is_student': role == 'STUDENT',

        # Parent portal
        'is_parent': role == 'PARENT',
    }
