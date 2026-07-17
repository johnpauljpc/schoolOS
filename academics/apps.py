"""
academics/apps.py

Application configuration for the academics app.
"""

from django.apps import AppConfig


class AcademicsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'academics'
    verbose_name       = 'Academics'

    def ready(self):
        """Import signal handlers when the app is ready (reserved for future use)."""
        pass  # noqa: unnecessary-pass
