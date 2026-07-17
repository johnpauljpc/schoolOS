from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.decorators import role_required


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN')
def settings_index(request):
    return render(request, 'settings_app/index.html')


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN')
def audit_logs(request):
    from core.models import AuditLog
    from core.utils import paginate_queryset
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')
    q = request.GET.get('q', '').strip()
    if q:
        from django.db.models import Q
        logs = logs.filter(Q(user__username__icontains=q) | Q(object_repr__icontains=q) | Q(action__icontains=q))
    logs_page = paginate_queryset(logs, request, per_page=50)
    return render(request, 'settings_app/audit_logs.html', {'logs': logs_page, 'q': q})


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN')
def login_activity(request):
    from accounts.models import LoginActivity
    from core.utils import paginate_queryset
    activities = LoginActivity.objects.select_related('user').order_by('-timestamp')
    activities_page = paginate_queryset(activities, request, per_page=50)
    return render(request, 'settings_app/login_activity.html', {'activities': activities_page})
