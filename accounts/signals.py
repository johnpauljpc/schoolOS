"""
accounts/signals.py
-------------------
Django signal handlers for the accounts app.

Responsibilities:
  - On new User creation:  generate an email verification token and send a
    welcome / verification email.
  - On User save (general): log meaningful field changes to core.AuditLog.
"""

import logging
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import AuditLog

User = get_user_model()
logger = logging.getLogger(__name__)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _send_welcome_verification_email(user):
    """
    Sends a combined welcome + email-verification email to a newly created user.
    The verification link embeds the user's email_verification_token.
    """
    if not user.email:
        logger.warning(
            'User %s has no email address; skipping welcome email.', user.username
        )
        return

    school_name = getattr(settings, 'SCHOOL_NAME', 'SchoolOS')
    verify_url = (
        f'{getattr(settings, "SITE_URL", "http://localhost:8000")}'
        f'/accounts/email/verify/{user.email_verification_token}/'
    )

    subject = f'Welcome to {school_name} — Please Verify Your Email'
    message = (
        f'Hello {user.first_name or user.username},\n\n'
        f'Your account on the {school_name} portal has been created successfully.\n\n'
        f'Username: {user.username}\n'
        f'Role:     {user.get_role_display()}\n\n'
        f'Please verify your email address by clicking the link below:\n'
        f'{verify_url}\n\n'
        f'If you did not expect this email, you can safely ignore it.\n\n'
        f'Best regards,\n'
        f'The {school_name} Team'
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info('Welcome/verification email sent to %s.', user.email)
    except Exception as exc:
        logger.error(
            'Failed to send welcome email to %s: %s', user.email, exc
        )


def _log_audit_for_user(user, action, changes='', ip_address=None):
    """Creates an AuditLog entry for a user-related action."""
    try:
        AuditLog.objects.create(
            user=None,          # system-level action (no request context here)
            action=action,
            model_name='User',
            object_id=str(user.pk),
            object_repr=str(user),
            changes=changes,
            ip_address=ip_address,
            extra_data={'triggered_by': 'signal'},
        )
    except Exception as exc:
        logger.error('AuditLog creation failed for user %s: %s', user.pk, exc)


# ─── Signal Receivers ──────────────────────────────────────────────────────────

@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Fires after every User save.

    On creation:
      1. Generate a UUID email-verification token and persist it.
      2. Send a welcome + verification email.
      3. Write a CREATE entry to AuditLog.

    On update:
      1. Write an UPDATE entry to AuditLog (generic; detailed field-level diffs
         are recorded in views that have access to form.changed_data).
    """
    if created:
        # ── Generate email verification token ──────────────────────────────
        if not instance.email_verification_token:
            # Use update_fields to avoid re-triggering the signal recursively
            User.objects.filter(pk=instance.pk).update(
                email_verification_token=str(uuid.uuid4())
            )
            # Refresh so the token is available for the email
            instance.refresh_from_db(fields=['email_verification_token'])

        # ── Send welcome email ─────────────────────────────────────────────
        _send_welcome_verification_email(instance)

        # ── Audit: CREATE ──────────────────────────────────────────────────
        _log_audit_for_user(
            user=instance,
            action='CREATE',
            changes=f'User created with role: {instance.get_role_display()}',
        )

    else:
        # ── Audit: UPDATE (signal-level, coarse-grained) ───────────────────
        # Fine-grained diffs are done inside views via form.changed_data.
        # Here we just record that the record was saved (e.g. via admin).
        _log_audit_for_user(
            user=instance,
            action='UPDATE',
            changes='User record updated (signal)',
        )
