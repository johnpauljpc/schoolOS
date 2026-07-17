from core.models import AuditLog


def get_client_ip(request):
    """Extract real client IP considering proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class AuditLogMiddleware:
    """
    Middleware that logs POST/PUT/DELETE actions to AuditLog.
    Captures login/logout events via Django signals instead.
    """
    EXCLUDED_PATHS = ['/static/', '/media/', '/favicon.ico']
    LOGGED_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Log write actions for authenticated users
        if (
            request.user.is_authenticated
            and request.method in self.LOGGED_METHODS
            and not any(request.path.startswith(p) for p in self.EXCLUDED_PATHS)
            and response.status_code in (200, 201, 302)
        ):
            try:
                action = 'CREATE' if request.method == 'POST' else 'UPDATE'
                if request.method == 'DELETE':
                    action = 'DELETE'
                AuditLog.objects.create(
                    user=request.user,
                    action=action,
                    object_repr=request.path,
                    ip_address=get_client_ip(request),
                )
            except Exception:
                pass  # Never break response due to logging errors
        return response
