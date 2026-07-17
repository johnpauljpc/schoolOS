"""
accounts/apps.py
----------------
AppConfig for the accounts app.
Imports signals in ready() so they are connected when Django starts.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'Accounts & Authentication'

    def ready(self):
        """Connect signal handlers when the app registry is fully populated."""
        import accounts.signals  # noqa: F401
