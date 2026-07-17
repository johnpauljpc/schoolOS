from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """
    Decorator that restricts view access to users with specific roles.
    Usage: @role_required('ADMIN', 'PRINCIPAL')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if hasattr(request.user, 'role') and request.user.role in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard:index')
        return _wrapped_view
    return decorator


def admin_required(view_func):
    """Shortcut for admin-only views."""
    return role_required('SUPER_ADMIN', 'ICT_ADMIN')(view_func)


def staff_required(view_func):
    """Allow any staff role."""
    return role_required(
        'SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'VICE_PRINCIPAL',
        'ADMISSION_OFFICER', 'ACCOUNTANT', 'TEACHER', 'CLASS_TEACHER'
    )(view_func)
