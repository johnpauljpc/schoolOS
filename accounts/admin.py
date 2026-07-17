"""
accounts/admin.py
-----------------
Custom Django admin registration for User and LoginActivity models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from accounts.models import LoginActivity, User


# ─── User Admin ────────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Extends Django's built-in UserAdmin to expose SchoolOS-specific fields
    such as role, phone, gender, avatar, and email verification status.
    """

    list_display = (
        'username',
        'full_name',
        'email',
        'role',
        'is_active',
        'is_email_verified',
        'date_joined',
    )
    list_display_links = ('username', 'full_name')
    list_filter = ('role', 'is_active', 'is_email_verified', 'gender', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')
    ordering = ('last_name', 'first_name')
    readonly_fields = ('date_joined', 'last_login', 'email_verification_token', 'password_reset_token')
    date_hierarchy = 'date_joined'

    # Fieldsets for the change (edit) form
    fieldsets = (
        (None, {
            'fields': ('username', 'password'),
        }),
        (_('Personal Information'), {
            'fields': (
                'first_name',
                'last_name',
                'email',
                'phone',
                'gender',
                'date_of_birth',
                'address',
                'avatar',
            ),
        }),
        (_('Role & Permissions'), {
            'fields': (
                'role',
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            ),
        }),
        (_('Email Verification'), {
            'fields': (
                'is_email_verified',
                'email_verification_token',
            ),
            'classes': ('collapse',),
        }),
        (_('Password Reset'), {
            'fields': (
                'password_reset_token',
                'password_reset_token_expires',
            ),
            'classes': ('collapse',),
        }),
        (_('Important Dates'), {
            'fields': ('last_login', 'date_joined'),
        }),
    )

    # Fieldsets for the add (create) form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'first_name',
                'last_name',
                'role',
                'phone',
                'password1',
                'password2',
                'is_active',
                'is_staff',
            ),
        }),
    )

    def full_name(self, obj):
        return obj.get_full_name() or '—'
    full_name.short_description = 'Full Name'
    full_name.admin_order_field = 'last_name'


# ─── LoginActivity Admin ───────────────────────────────────────────────────────

@admin.register(LoginActivity)
class LoginActivityAdmin(admin.ModelAdmin):
    """Read-only admin view for login audit records."""

    list_display = (
        'username_attempted',
        'user',
        'status',
        'ip_address',
        'timestamp',
    )
    list_filter = ('status', 'timestamp')
    search_fields = ('username_attempted', 'ip_address', 'user__username', 'user__email')
    readonly_fields = (
        'user',
        'username_attempted',
        'ip_address',
        'user_agent',
        'status',
        'timestamp',
    )
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        """Login activities are created programmatically; block manual creation."""
        return False

    def has_change_permission(self, request, obj=None):
        """Login activities are immutable audit records."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Only superusers may delete login activity records."""
        return request.user.is_superuser
