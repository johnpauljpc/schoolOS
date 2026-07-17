"""
accounts/forms.py
-----------------
All forms used by the accounts app of SchoolOS.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.models import Role, Gender

User = get_user_model()


# ─── Authentication Forms ──────────────────────────────────────────────────────

class LoginForm(forms.Form):
    """Simple username + password login form."""

    username = forms.CharField(
        max_length=150,
        label=_('Username'),
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your username',
            'autofocus': True,
            'autocomplete': 'username',
        }),
    )
    password = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        }),
    )
    remember_me = forms.BooleanField(
        required=False,
        label=_('Remember me'),
        initial=False,
    )


# ─── Profile Forms ─────────────────────────────────────────────────────────────

class ProfileUpdateForm(forms.ModelForm):
    """Allows a user to update their own profile information."""

    date_of_birth = forms.DateField(
        required=False,
        label=_('Date of Birth'),
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'gender',
            'date_of_birth',
            'address',
            'avatar',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone number'}),
            'gender': forms.Select(choices=[('', '— Select Gender —')] + list(Gender.choices)),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Home address'}),
            'avatar': forms.FileInput(),
        }
        labels = {
            'first_name': _('First Name'),
            'last_name': _('Last Name'),
            'email': _('Email Address'),
            'phone': _('Phone Number'),
            'gender': _('Gender'),
            'address': _('Address'),
            'avatar': _('Profile Photo'),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(_('A user with this email already exists.'))
        return email

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'size'):
            max_size = 2 * 1024 * 1024  # 2 MB
            if avatar.size > max_size:
                raise ValidationError(_('Image file must be smaller than 2 MB.'))
        return avatar


# ─── Password Forms ────────────────────────────────────────────────────────────

class CustomPasswordChangeForm(PasswordChangeForm):
    """Extends Django's built-in PasswordChangeForm with custom styling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget = forms.PasswordInput(attrs={
            'placeholder': 'Current password',
            'autocomplete': 'current-password',
        })
        self.fields['new_password1'].widget = forms.PasswordInput(attrs={
            'placeholder': 'New password',
            'autocomplete': 'new-password',
        })
        self.fields['new_password2'].widget = forms.PasswordInput(attrs={
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password',
        })
        self.fields['old_password'].label = _('Current Password')
        self.fields['new_password1'].label = _('New Password')
        self.fields['new_password2'].label = _('Confirm New Password')


class PasswordResetRequestForm(forms.Form):
    """Collects an email address to initiate password reset."""

    email = forms.EmailField(
        label=_('Email Address'),
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your registered email address',
            'autocomplete': 'email',
        }),
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email__iexact=email, is_active=True).exists():
            # Deliberately vague: do not leak whether the email is registered.
            # Actual view will still silently succeed.
            pass
        return email


class SetNewPasswordForm(forms.Form):
    """Shown after clicking a password reset link; sets a new password."""

    new_password1 = forms.CharField(
        label=_('New Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password',
        }),
    )
    new_password2 = forms.CharField(
        label=_('Confirm New Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password',
        }),
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError(_('The two passwords did not match.'))
        return cleaned_data

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        if password:
            from django.contrib.auth.password_validation import validate_password
            validate_password(password)
        return password


# ─── Admin / User Management Forms ────────────────────────────────────────────

class UserCreateForm(forms.ModelForm):
    """
    Used by admins to create a new portal user.
    Includes role assignment and password setting.
    """

    password1 = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Set a password'}),
    )
    password2 = forms.CharField(
        label=_('Confirm Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password'}),
    )

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'phone',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Login username'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'role': forms.Select(choices=[('', '— Select Role —')] + list(Role.choices)),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone number'}),
        }
        labels = {
            'username': _('Username'),
            'email': _('Email Address'),
            'first_name': _('First Name'),
            'last_name': _('Last Name'),
            'role': _('Role'),
            'phone': _('Phone Number'),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(_('A user with this username already exists.'))
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_('A user with this email already exists.'))
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', _('Passwords do not match.'))
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    """
    Used by admins to update an existing user's details.
    Does not handle password changes.
    """

    date_of_birth = forms.DateField(
        required=False,
        label=_('Date of Birth'),
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'phone',
            'gender',
            'date_of_birth',
            'address',
            'is_active',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Login username'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'role': forms.Select(choices=[('', '— Select Role —')] + list(Role.choices)),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone number'}),
            'gender': forms.Select(choices=[('', '— Select Gender —')] + list(Gender.choices)),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(_('A user with this email already exists.'))
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        qs = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(_('A user with this username already exists.'))
        return username
