"""
accounts/views.py
-----------------
All views for authentication, profile management, and user administration
in the SchoolOS accounts app.
"""

import uuid
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    get_user_model,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.models import LoginActivity, Role
from accounts.forms import (
    CustomPasswordChangeForm,
    LoginForm,
    PasswordResetRequestForm,
    ProfileUpdateForm,
    SetNewPasswordForm,
    UserCreateForm,
    UserUpdateForm,
)
from core.decorators import admin_required
from core.models import AuditLog

User = get_user_model()
logger = logging.getLogger(__name__)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_client_ip(request):
    """Extract the real client IP, honouring X-Forwarded-For."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _get_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', '')


def _log_login_activity(user, username_attempted, ip, user_agent, status):
    """Create a LoginActivity record."""
    LoginActivity.objects.create(
        user=user,
        username_attempted=username_attempted,
        ip_address=ip,
        user_agent=user_agent,
        status=status,
    )


def _log_audit(user, action, model_name='', object_id='', object_repr='',
               changes='', ip_address=None, extra_data=None):
    """Create a core AuditLog entry."""
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        object_repr=object_repr,
        changes=changes,
        ip_address=ip_address,
        extra_data=extra_data or {},
    )


# ─── Authentication Views ──────────────────────────────────────────────────────

def login_view(request):
    """
    Authenticates a user, records LoginActivity, and redirects to dashboard.
    Supports ?next= parameter for post-login redirect.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    form = LoginForm(request.POST or None)
    ip = _get_client_ip(request)
    ua = _get_user_agent(request)

    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        remember_me = form.cleaned_data.get('remember_me', False)

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                _log_login_activity(user, username, ip, ua, 'FAILED')
                messages.error(request, 'Your account has been deactivated. Contact the administrator.')
                return render(request, 'accounts/login.html', {'form': form})

            login(request, user)

            # Session expiry based on "remember me"
            if not remember_me:
                request.session.set_expiry(0)  # expires on browser close
            else:
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)

            _log_login_activity(user, username, ip, ua, 'SUCCESS')
            _log_audit(
                user=user,
                action='LOGIN',
                model_name='User',
                object_id=user.pk,
                object_repr=str(user),
                ip_address=ip,
                extra_data={'user_agent': ua},
            )

            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            next_url = request.POST.get('next') or request.GET.get('next') or '/dashboard/'
            # Safety: only allow relative URLs
            if next_url and not next_url.startswith('/'):
                next_url = '/dashboard/'
            return redirect(next_url)

        else:
            # Try to find the user to attach to the failed activity record
            failed_user = User.objects.filter(username__iexact=username).first()
            _log_login_activity(failed_user, username, ip, ua, 'FAILED')
            messages.error(request, 'Invalid username or password.')

    next_url = request.GET.get('next', '')
    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


@login_required
def logout_view(request):
    """
    Logs out the current user, records LoginActivity and AuditLog.
    Accepts both GET and POST for flexibility (e.g., CSRF-protected form or simple link).
    """
    ip = _get_client_ip(request)
    ua = _get_user_agent(request)
    user = request.user

    _log_login_activity(user, user.username, ip, ua, 'LOGOUT')
    _log_audit(
        user=user,
        action='LOGOUT',
        model_name='User',
        object_id=user.pk,
        object_repr=str(user),
        ip_address=ip,
        extra_data={'user_agent': ua},
    )

    logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('accounts:login')


# ─── Profile Views ─────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    """Displays the authenticated user's profile page."""
    user = request.user
    recent_logins = LoginActivity.objects.filter(user=user).order_by('-timestamp')[:10]
    context = {
        'user': user,
        'recent_logins': recent_logins,
        'page_title': 'My Profile',
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_update_view(request):
    """Allows the authenticated user to update their profile information."""
    user = request.user
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            updated_user = form.save(commit=False)
            # If email changed, mark as unverified and send verification email
            if 'email' in form.changed_data and updated_user.email:
                updated_user.is_email_verified = False
                updated_user.email_verification_token = str(uuid.uuid4())
            updated_user.save()
            _log_audit(
                user=user,
                action='UPDATE',
                model_name='User',
                object_id=user.pk,
                object_repr=str(user),
                changes=', '.join(form.changed_data),
                ip_address=_get_client_ip(request),
            )
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, 'accounts/profile_update.html', {
        'form': form,
        'page_title': 'Update Profile',
    })


# ─── Password Views ────────────────────────────────────────────────────────────

@login_required
def change_password_view(request):
    """Allows an authenticated user to change their password."""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # Keep the user logged in after password change
            update_session_auth_hash(request, form.user)
            _log_audit(
                user=request.user,
                action='UPDATE',
                model_name='User',
                object_id=request.user.pk,
                object_repr=str(request.user),
                changes='password changed',
                ip_address=_get_client_ip(request),
            )
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'accounts/change_password.html', {
        'form': form,
        'page_title': 'Change Password',
    })


def password_reset_request_view(request):
    """
    Accepts an email address and sends a password reset link.
    Generates a UUID token stored on the User model (password_reset_token).
    """
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user:
                token = str(uuid.uuid4())
                user.password_reset_token = token
                user.password_reset_token_expires = timezone.now() + timedelta(hours=2)
                user.save(update_fields=['password_reset_token', 'password_reset_token_expires'])

                reset_url = request.build_absolute_uri(
                    f'/accounts/password-reset/confirm/{token}/'
                )
                try:
                    send_mail(
                        subject='SchoolOS — Password Reset Request',
                        message=(
                            f'Hello {user.first_name or user.username},\n\n'
                            f'You requested a password reset for your SchoolOS account.\n'
                            f'Click the link below to set a new password (valid for 2 hours):\n\n'
                            f'{reset_url}\n\n'
                            f'If you did not request this, please ignore this email.\n\n'
                            f'— SchoolOS Team'
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    logger.info('Password reset email sent to %s', user.email)
                except Exception as exc:
                    logger.error('Failed to send password reset email to %s: %s', user.email, exc)

            # Always show success message to prevent user enumeration
            messages.success(
                request,
                'If that email is registered, you will receive a reset link shortly.'
            )
            return redirect('accounts:login')
    else:
        form = PasswordResetRequestForm()

    return render(request, 'accounts/password_reset_request.html', {
        'form': form,
        'page_title': 'Reset Password',
    })


def password_reset_confirm_view(request, token):
    """
    Validates the password reset token from the URL and allows the user
    to set a new password.
    """
    user = User.objects.filter(
        password_reset_token=token,
        password_reset_token_expires__gt=timezone.now(),
        is_active=True,
    ).first()

    if user is None:
        messages.error(
            request,
            'This password reset link is invalid or has expired. Please request a new one.'
        )
        return redirect('accounts:password_reset_request')

    if request.method == 'POST':
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password1'])
            # Clear the token so it cannot be reused
            user.password_reset_token = ''
            user.password_reset_token_expires = None
            user.save(update_fields=['password', 'password_reset_token', 'password_reset_token_expires'])
            _log_audit(
                user=user,
                action='UPDATE',
                model_name='User',
                object_id=user.pk,
                object_repr=str(user),
                changes='password reset via email link',
                ip_address=_get_client_ip(request),
            )
            messages.success(request, 'Your password has been reset. You can now log in.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SetNewPasswordForm()

    return render(request, 'accounts/password_reset_confirm.html', {
        'form': form,
        'token': token,
        'page_title': 'Set New Password',
    })


# ─── Email Verification ────────────────────────────────────────────────────────

def email_verify_view(request, token):
    """
    Verifies the user's email address via the token embedded in the
    verification link sent on registration or email change.
    """
    user = User.objects.filter(email_verification_token=token, is_active=True).first()

    if user is None:
        messages.error(request, 'This email verification link is invalid or has already been used.')
        return redirect('accounts:login')

    user.is_email_verified = True
    user.email_verification_token = ''
    user.save(update_fields=['is_email_verified', 'email_verification_token'])

    _log_audit(
        user=user,
        action='UPDATE',
        model_name='User',
        object_id=user.pk,
        object_repr=str(user),
        changes='email verified',
        ip_address=_get_client_ip(request),
    )
    messages.success(request, 'Your email address has been verified successfully.')
    return redirect('accounts:profile' if request.user.is_authenticated else 'accounts:login')


# ─── Admin: User Management Views ─────────────────────────────────────────────

@login_required
@admin_required
def user_list_view(request):
    """
    Admin-only view listing all portal users.
    Supports search by name, username, email, and role filtering.
    """
    queryset = User.objects.all().order_by('last_name', 'first_name')

    # Search
    query = request.GET.get('q', '').strip()
    if query:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    # Role filter
    role_filter = request.GET.get('role', '').strip()
    if role_filter and role_filter in Role.values:
        queryset = queryset.filter(role=role_filter)

    # Active filter
    active_filter = request.GET.get('is_active', '').strip()
    if active_filter == '1':
        queryset = queryset.filter(is_active=True)
    elif active_filter == '0':
        queryset = queryset.filter(is_active=False)

    # Pagination
    paginator = Paginator(queryset, 25)
    page = request.GET.get('page', 1)
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)

    context = {
        'users': users,
        'query': query,
        'role_filter': role_filter,
        'active_filter': active_filter,
        'roles': Role.choices,
        'page_title': 'User Management',
        'total_count': queryset.count(),
    }
    return render(request, 'accounts/user_list.html', context)


@login_required
@admin_required
def user_create_view(request):
    """Admin-only view for creating a new portal user."""
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            _log_audit(
                user=request.user,
                action='CREATE',
                model_name='User',
                object_id=new_user.pk,
                object_repr=str(new_user),
                changes=f'Created user: {new_user.username}, role: {new_user.get_role_display()}',
                ip_address=_get_client_ip(request),
            )
            messages.success(
                request,
                f'User "{new_user.username}" has been created successfully.'
            )
            return redirect('accounts:user_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreateForm()

    return render(request, 'accounts/user_create.html', {
        'form': form,
        'page_title': 'Create New User',
    })


@login_required
@admin_required
def user_update_view(request, pk):
    """Admin-only view for updating an existing user's details."""
    target_user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=target_user)
        if form.is_valid():
            changed = form.changed_data
            form.save()
            _log_audit(
                user=request.user,
                action='UPDATE',
                model_name='User',
                object_id=target_user.pk,
                object_repr=str(target_user),
                changes=', '.join(changed),
                ip_address=_get_client_ip(request),
            )
            messages.success(
                request,
                f'User "{target_user.username}" has been updated successfully.'
            )
            return redirect('accounts:user_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserUpdateForm(instance=target_user)

    return render(request, 'accounts/user_update.html', {
        'form': form,
        'target_user': target_user,
        'page_title': f'Update User — {target_user.username}',
    })


@login_required
@admin_required
@require_http_methods(['POST'])
def user_toggle_active_view(request, pk):
    """
    Admin-only POST endpoint to toggle a user's is_active status.
    Designed for use with a small form button in the user list.
    """
    target_user = get_object_or_404(User, pk=pk)

    # Prevent admins from deactivating themselves
    if target_user == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('accounts:user_list')

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=['is_active'])

    status_label = 'activated' if target_user.is_active else 'deactivated'
    _log_audit(
        user=request.user,
        action='UPDATE',
        model_name='User',
        object_id=target_user.pk,
        object_repr=str(target_user),
        changes=f'Account {status_label}',
        ip_address=_get_client_ip(request),
    )
    messages.success(
        request,
        f'User "{target_user.username}" has been {status_label}.'
    )
    return redirect('accounts:user_list')
