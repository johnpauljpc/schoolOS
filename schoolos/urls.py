from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    return redirect('accounts:login')


urlpatterns = [
    path('', root_redirect, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('students/', include('students.urls', namespace='students')),
    path('staff/', include('staff.urls', namespace='staff')),
    path('academics/', include('academics.urls', namespace='academics')),
    path('admissions/', include('admissions.urls', namespace='admissions')),
    path('examinations/', include('examinations.urls', namespace='examinations')),
    path('finance/', include('finance.urls', namespace='finance')),
    path('communication/', include('communication.urls', namespace='communication')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('settings/', include('settings_app.urls', namespace='settings_app')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else None)
