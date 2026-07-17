"""
staff/forms.py
--------------
All forms for the staff app of SchoolOS.

Covers:
  - StaffUserCreateForm      — create User (appropriate role) + Staff + optional Teacher profile
  - StaffForm                — update Staff profile fields
  - StaffSearchForm          — search & filter on the staff list
  - StaffQualificationForm   — add a qualification record
  - TeacherForm              — update Teacher-specific fields
"""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from academics.models import ClassArm, Department, Subject
from accounts.models import Gender, Role
from staff.models import (
    EmploymentType,
    QualificationLevel,
    Staff,
    StaffQualification,
    Teacher,
)

User = get_user_model()


# ─── Helpers ───────────────────────────────────────────────────────────────────

STAFF_ROLES = [
    (Role.TEACHER, Role.TEACHER.label),
    (Role.CLASS_TEACHER, Role.CLASS_TEACHER.label),
    (Role.PRINCIPAL, Role.PRINCIPAL.label),
    (Role.VICE_PRINCIPAL, Role.VICE_PRINCIPAL.label),
    (Role.ADMISSION_OFFICER, Role.ADMISSION_OFFICER.label),
    (Role.ACCOUNTANT, Role.ACCOUNTANT.label),
    (Role.ICT_ADMIN, Role.ICT_ADMIN.label),
]


# ─── Staff Create Form ─────────────────────────────────────────────────────────

class StaffUserCreateForm(forms.Form):
    """
    Combined form used by staff_create_view.
    Creates a User (appropriate staff role) + Staff profile in one atomic POST.
    Also optionally creates a Teacher profile if role is TEACHER or CLASS_TEACHER.
    """

    # User fields
    first_name = forms.CharField(
        max_length=150, label=_('First Name'),
        widget=forms.TextInput(attrs={'placeholder': 'First name'}),
    )
    last_name = forms.CharField(
        max_length=150, label=_('Last Name'),
        widget=forms.TextInput(attrs={'placeholder': 'Last name'}),
    )
    username = forms.CharField(
        max_length=150, label=_('Username'),
        widget=forms.TextInput(attrs={'placeholder': 'Login username'}),
    )
    email = forms.EmailField(
        required=False, label=_('Email Address'),
        widget=forms.EmailInput(attrs={'placeholder': 'staff@school.edu'}),
    )
    phone = forms.CharField(
        max_length=20, required=False, label=_('Phone Number'),
        widget=forms.TextInput(attrs={'placeholder': '+234…'}),
    )
    gender = forms.ChoiceField(
        choices=[('', '— Select Gender —')] + list(Gender.choices),
        required=False, label=_('Gender'),
    )
    date_of_birth = forms.DateField(
        required=False, label=_('Date of Birth'),
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    address = forms.CharField(
        required=False, label=_('Address'),
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Home address'}),
    )
    role = forms.ChoiceField(
        choices=[('', '— Select Role —')] + STAFF_ROLES,
        label=_('Role'),
    )
    password = forms.CharField(
        label=_('Password'), strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Set a password'}),
    )
    confirm_password = forms.CharField(
        label=_('Confirm Password'), strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password'}),
    )

    # Staff profile fields
    staff_id = forms.CharField(
        max_length=20, label=_('Staff ID'),
        widget=forms.TextInput(attrs={'placeholder': 'e.g. STF/2024/001'}),
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.order_by('name'),
        required=False, label=_('Department'),
        empty_label='— Select Department —',
    )
    designation = forms.CharField(
        max_length=100, required=False, label=_('Designation'),
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Senior Teacher'}),
    )
    employment_type = forms.ChoiceField(
        choices=EmploymentType.choices,
        initial=EmploymentType.FULL_TIME,
        label=_('Employment Type'),
    )
    date_joined = forms.DateField(
        required=False, label=_('Date Joined'),
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    salary = forms.DecimalField(
        required=False, max_digits=12, decimal_places=2,
        label=_('Salary (₦)'),
        widget=forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
    )
    bank_name = forms.CharField(
        max_length=100, required=False, label=_('Bank Name'),
        widget=forms.TextInput(attrs={'placeholder': 'Bank name'}),
    )
    account_number = forms.CharField(
        max_length=20, required=False, label=_('Account Number'),
        widget=forms.TextInput(attrs={'placeholder': '0123456789'}),
    )
    account_name = forms.CharField(
        max_length=200, required=False, label=_('Account Name'),
        widget=forms.TextInput(attrs={'placeholder': 'Account name'}),
    )
    notes = forms.CharField(
        required=False, label=_('Notes'),
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Additional notes…'}),
    )

    # Teacher-specific fields (only used when role == TEACHER / CLASS_TEACHER)
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.order_by('name'),
        required=False, label=_('Subjects Taught'),
        widget=forms.CheckboxSelectMultiple,
    )
    class_assigned = forms.ModelChoiceField(
        queryset=ClassArm.objects.select_related('class_level').order_by(
            'class_level__order', 'name'
        ),
        required=False, label=_('Form Class Assigned'),
        empty_label='— None —',
    )
    specialization = forms.CharField(
        max_length=200, required=False, label=_('Specialization'),
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Sciences'}),
    )
    years_of_experience = forms.IntegerField(
        required=False, initial=0, label=_('Years of Experience'),
        widget=forms.NumberInput(attrs={'min': '0'}),
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(_('A user with this username already exists.'))
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_('A user with this email already exists.'))
        return email

    def clean_staff_id(self):
        staff_id = self.cleaned_data.get('staff_id', '').strip()
        if Staff.objects.filter(staff_id__iexact=staff_id).exists():
            raise ValidationError(_('A staff member with this ID already exists.'))
        return staff_id

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', _('Passwords do not match.'))
        return cleaned


# ─── Staff Update Form ─────────────────────────────────────────────────────────

class StaffForm(forms.ModelForm):
    """Update an existing Staff member's profile (not the linked User)."""

    date_joined = forms.DateField(
        required=False, label=_('Date Joined'),
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    date_left = forms.DateField(
        required=False, label=_('Date Left'),
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    class Meta:
        model = Staff
        fields = [
            'staff_id',
            'department',
            'designation',
            'employment_type',
            'date_joined',
            'date_left',
            'is_active',
            'salary',
            'bank_name',
            'account_number',
            'account_name',
            'notes',
        ]
        widgets = {
            'staff_id': forms.TextInput(attrs={'placeholder': 'e.g. STF/2024/001'}),
            'designation': forms.TextInput(attrs={'placeholder': 'e.g. Senior Teacher'}),
            'salary': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
            'bank_name': forms.TextInput(attrs={'placeholder': 'Bank name'}),
            'account_number': forms.TextInput(attrs={'placeholder': '0123456789'}),
            'account_name': forms.TextInput(attrs={'placeholder': 'Account name'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'staff_id': _('Staff ID'),
            'department': _('Department'),
            'designation': _('Designation'),
            'employment_type': _('Employment Type'),
            'date_joined': _('Date Joined'),
            'date_left': _('Date Left'),
            'is_active': _('Active'),
            'salary': _('Salary (₦)'),
            'bank_name': _('Bank Name'),
            'account_number': _('Account Number'),
            'account_name': _('Account Name'),
            'notes': _('Notes'),
        }

    def clean_staff_id(self):
        staff_id = self.cleaned_data.get('staff_id', '').strip()
        qs = Staff.objects.filter(staff_id__iexact=staff_id)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(_('A staff member with this ID already exists.'))
        return staff_id


# ─── Staff Search Form ─────────────────────────────────────────────────────────

class StaffSearchForm(forms.Form):
    """Search & filter form used on the staff list page."""

    search_query = forms.CharField(
        required=False, label=_('Search'),
        widget=forms.TextInput(attrs={
            'placeholder': 'Name, staff ID, department…',
            'autocomplete': 'off',
        }),
    )
    employment_type = forms.ChoiceField(
        required=False, label=_('Employment Type'),
        choices=[('', 'All Types')] + list(EmploymentType.choices),
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.order_by('name'),
        required=False, label=_('Department'),
        empty_label='All Departments',
    )
    is_active = forms.ChoiceField(
        required=False, label=_('Status'),
        choices=[('', 'All'), ('1', 'Active'), ('0', 'Inactive')],
    )


# ─── Qualification Form ────────────────────────────────────────────────────────

class StaffQualificationForm(forms.ModelForm):
    """Add a qualification record for a staff member."""

    year_obtained = forms.IntegerField(
        required=False, label=_('Year Obtained'),
        widget=forms.NumberInput(attrs={'placeholder': 'e.g. 2015', 'min': '1960', 'max': '2100'}),
    )

    class Meta:
        model = StaffQualification
        fields = ['level', 'institution', 'course', 'year_obtained', 'certificate']
        widgets = {
            'level': forms.Select(),
            'institution': forms.TextInput(attrs={'placeholder': 'Institution name'}),
            'course': forms.TextInput(attrs={'placeholder': 'Course of study'}),
            'certificate': forms.FileInput(),
        }
        labels = {
            'level': _('Qualification Level'),
            'institution': _('Institution'),
            'course': _('Course / Field of Study'),
            'year_obtained': _('Year Obtained'),
            'certificate': _('Certificate File'),
        }

    def clean_certificate(self):
        cert = self.cleaned_data.get('certificate')
        if cert and hasattr(cert, 'size'):
            max_size = 5 * 1024 * 1024  # 5 MB
            if cert.size > max_size:
                raise ValidationError(_('Certificate file must be smaller than 5 MB.'))
        return cert


# ─── Teacher Form ──────────────────────────────────────────────────────────────

class TeacherForm(forms.ModelForm):
    """Update Teacher-specific profile details."""

    class Meta:
        model = Teacher
        fields = ['subjects', 'class_assigned', 'specialization', 'years_of_experience']
        widgets = {
            'subjects': forms.CheckboxSelectMultiple,
            'class_assigned': forms.Select(),
            'specialization': forms.TextInput(attrs={'placeholder': 'e.g. Sciences'}),
            'years_of_experience': forms.NumberInput(attrs={'min': '0'}),
        }
        labels = {
            'subjects': _('Subjects Taught'),
            'class_assigned': _('Form Class Assigned'),
            'specialization': _('Specialization'),
            'years_of_experience': _('Years of Experience'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subjects'].queryset = Subject.objects.select_related(
            'department'
        ).order_by('name')
        self.fields['class_assigned'].queryset = ClassArm.objects.select_related(
            'class_level'
        ).order_by('class_level__order', 'name')
        self.fields['class_assigned'].empty_label = '— None (not a form teacher) —'
