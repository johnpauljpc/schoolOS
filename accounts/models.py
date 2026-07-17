from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    SUPER_ADMIN = 'SUPER_ADMIN', 'Super Administrator'
    ICT_ADMIN = 'ICT_ADMIN', 'ICT Administrator'
    PRINCIPAL = 'PRINCIPAL', 'Principal'
    VICE_PRINCIPAL = 'VICE_PRINCIPAL', 'Vice Principal'
    ADMISSION_OFFICER = 'ADMISSION_OFFICER', 'Admission Officer'
    ACCOUNTANT = 'ACCOUNTANT', 'Accountant'
    TEACHER = 'TEACHER', 'Teacher'
    CLASS_TEACHER = 'CLASS_TEACHER', 'Class Teacher'
    STUDENT = 'STUDENT', 'Student'
    PARENT = 'PARENT', 'Parent'


class Gender(models.TextChoices):
    MALE = 'MALE', 'Male'
    FEMALE = 'FEMALE', 'Female'
    OTHER = 'OTHER', 'Other'


class User(AbstractUser):
    """
    Custom user model for SchoolOS.
    Extends AbstractUser with role, contact, and verification fields.
    """
    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name=_('Role'),
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name=_('Phone'))
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True, blank=True,
        verbose_name=_('Profile Photo')
    )
    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_('Date of Birth'))
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        blank=True,
        verbose_name=_('Gender')
    )
    address = models.TextField(blank=True, verbose_name=_('Address'))
    is_email_verified = models.BooleanField(default=False, verbose_name=_('Email Verified'))
    email_verification_token = models.CharField(max_length=100, blank=True)
    password_reset_token = models.CharField(max_length=100, blank=True)
    password_reset_token_expires = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    @property
    def is_admin(self):
        return self.role in [Role.SUPER_ADMIN, Role.ICT_ADMIN]

    @property
    def is_staff_member(self):
        return self.role in [
            Role.SUPER_ADMIN, Role.ICT_ADMIN, Role.PRINCIPAL, Role.VICE_PRINCIPAL,
            Role.ADMISSION_OFFICER, Role.ACCOUNTANT, Role.TEACHER, Role.CLASS_TEACHER
        ]

    @property
    def is_student_user(self):
        return self.role == Role.STUDENT

    @property
    def is_parent_user(self):
        return self.role == Role.PARENT

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return '/static/img/default_avatar.svg'


class LoginActivity(models.Model):
    """Tracks login attempts and sessions."""
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('LOGOUT', 'Logout'),
    ]
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='login_activities', null=True, blank=True
    )
    username_attempted = models.CharField(max_length=150, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Login Activity'
        verbose_name_plural = 'Login Activities'

    def __str__(self):
        return f"{self.username_attempted} — {self.status} @ {self.timestamp:%Y-%m-%d %H:%M}"
