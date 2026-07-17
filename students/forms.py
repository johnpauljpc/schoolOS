"""
students/forms.py
-----------------
All forms for the students app of SchoolOS.

Covers:
  - StudentForm          — update Student profile fields
  - StudentUserCreateForm — create User + Student in one form
  - StudentSearchForm    — search & filter on the student list
  - ParentForm           — create / update Parent profile
  - ParentUserCreateForm — create User + Parent in one form
  - MedicalInfoForm      — create / update MedicalInfo
  - StudentDocumentForm  — upload a StudentDocument
  - StudentPromotionForm — bulk-promote students to a new class/session
"""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from academics.models import AcademicSession, ClassArm
from accounts.models import Gender, Role
from students.models import (
    MedicalInfo,
    Parent,
    Student,
    StudentDocument,
    StudentStatus,
)

User = get_user_model()


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _class_arm_queryset():
    return ClassArm.objects.select_related('class_level').order_by(
        'class_level__order', 'name'
    )


# ─── Student Forms ─────────────────────────────────────────────────────────────

class StudentUserCreateForm(forms.Form):
    """
    Combined form used by student_create_view.
    Creates a User (role=STUDENT) and a Student profile in a single POST.
    """

    # --- User fields ---
    first_name = forms.CharField(
        max_length=150,
        label=_('First Name'),
        widget=forms.TextInput(attrs={'placeholder': 'First name'}),
    )
    last_name = forms.CharField(
        max_length=150,
        label=_('Last Name'),
        widget=forms.TextInput(attrs={'placeholder': 'Last name'}),
    )
    username = forms.CharField(
        max_length=150,
        label=_('Username'),
        widget=forms.TextInput(attrs={'placeholder': 'Login username'}),
    )
    email = forms.EmailField(
        required=False,
        label=_('Email Address'),
        widget=forms.EmailInput(attrs={'placeholder': 'student@school.edu'}),
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        label=_('Phone Number'),
        widget=forms.TextInput(attrs={'placeholder': '+234…'}),
    )
    gender = forms.ChoiceField(
        choices=[('', '— Select Gender —')] + list(Gender.choices),
        required=False,
        label=_('Gender'),
    )
    date_of_birth = forms.DateField(
        required=False,
        label=_('Date of Birth'),
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    address = forms.CharField(
        required=False,
        label=_('Home Address'),
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Home address'}),
    )
    password = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Set a password'}),
    )
    confirm_password = forms.CharField(
        label=_('Confirm Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password'}),
    )

    # --- Student profile fields ---
    admission_number = forms.CharField(
        max_length=20,
        label=_('Admission Number'),
        widget=forms.TextInput(attrs={'placeholder': 'e.g. ADM/2024/001'}),
    )
    class_enrolled = forms.ModelChoiceField(
        queryset=ClassArm.objects.none(),
        required=False,
        label=_('Class Enrolled'),
        empty_label='— Select Class —',
    )
    date_admitted = forms.DateField(
        required=False,
        label=_('Date Admitted'),
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    status = forms.ChoiceField(
        choices=StudentStatus.choices,
        initial=StudentStatus.ACTIVE,
        label=_('Status'),
    )
    religion = forms.CharField(
        max_length=50, required=False,
        label=_('Religion'),
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Christianity'}),
    )
    nationality = forms.CharField(
        max_length=50,
        initial='Nigerian',
        label=_('Nationality'),
        widget=forms.TextInput(attrs={'placeholder': 'Nigerian'}),
    )
    state_of_origin = forms.CharField(
        max_length=50, required=False,
        label=_('State of Origin'),
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Lagos'}),
    )
    lga = forms.CharField(
        max_length=100, required=False,
        label=_('LGA'),
        widget=forms.TextInput(attrs={'placeholder': 'Local Government Area'}),
    )
    previous_school = forms.CharField(
        max_length=200, required=False,
        label=_('Previous School'),
        widget=forms.TextInput(attrs={'placeholder': 'Previous school name'}),
    )
    notes = forms.CharField(
        required=False,
        label=_('Notes'),
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Additional notes…'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['class_enrolled'].queryset = _class_arm_queryset()

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

    def clean_admission_number(self):
        adm = self.cleaned_data.get('admission_number', '').strip()
        if Student.objects.filter(admission_number__iexact=adm).exists():
            raise ValidationError(_('A student with this admission number already exists.'))
        return adm

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', _('Passwords do not match.'))
        return cleaned


class StudentForm(forms.ModelForm):
    """
    ModelForm for updating an existing Student's profile fields.
    Does NOT touch the linked User account.
    """

    date_admitted = forms.DateField(
        required=False,
        label=_('Date Admitted'),
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    class Meta:
        model = Student
        fields = [
            'admission_number',
            'class_enrolled',
            'date_admitted',
            'status',
            'religion',
            'nationality',
            'state_of_origin',
            'lga',
            'previous_school',
            'notes',
        ]
        widgets = {
            'admission_number': forms.TextInput(attrs={'placeholder': 'e.g. ADM/2024/001'}),
            'class_enrolled': forms.Select(),
            'status': forms.Select(),
            'religion': forms.TextInput(attrs={'placeholder': 'e.g. Christianity'}),
            'nationality': forms.TextInput(attrs={'placeholder': 'Nigerian'}),
            'state_of_origin': forms.TextInput(attrs={'placeholder': 'e.g. Lagos'}),
            'lga': forms.TextInput(attrs={'placeholder': 'Local Government Area'}),
            'previous_school': forms.TextInput(attrs={'placeholder': 'Previous school name'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'lga': _('LGA'),
            'class_enrolled': _('Class Enrolled'),
            'date_admitted': _('Date Admitted'),
            'previous_school': _('Previous School'),
            'state_of_origin': _('State of Origin'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['class_enrolled'].queryset = _class_arm_queryset()
        self.fields['class_enrolled'].empty_label = '— Select Class —'

    def clean_admission_number(self):
        adm = self.cleaned_data.get('admission_number', '').strip()
        qs = Student.objects.filter(admission_number__iexact=adm)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(_('A student with this admission number already exists.'))
        return adm


class StudentSearchForm(forms.Form):
    """Search & filter form used on the student list page."""

    search_query = forms.CharField(
        required=False,
        label=_('Search'),
        widget=forms.TextInput(attrs={
            'placeholder': 'Name, admission number, class…',
            'autocomplete': 'off',
        }),
    )
    status = forms.ChoiceField(
        required=False,
        label=_('Status'),
        choices=[('', 'All Statuses')] + list(StudentStatus.choices),
    )
    class_enrolled = forms.ModelChoiceField(
        queryset=ClassArm.objects.none(),
        required=False,
        label=_('Class'),
        empty_label='All Classes',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['class_enrolled'].queryset = _class_arm_queryset()


# ─── Parent Forms ──────────────────────────────────────────────────────────────

class ParentUserCreateForm(forms.Form):
    """
    Combined form used by parent_create_view.
    Creates a User (role=PARENT) + Parent profile in one POST.
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
        widget=forms.EmailInput(attrs={'placeholder': 'parent@example.com'}),
    )
    phone = forms.CharField(
        max_length=20, required=False, label=_('Phone Number'),
        widget=forms.TextInput(attrs={'placeholder': '+234…'}),
    )
    gender = forms.ChoiceField(
        choices=[('', '— Select Gender —')] + list(Gender.choices),
        required=False, label=_('Gender'),
    )
    address = forms.CharField(
        required=False, label=_('Address'),
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Home address'}),
    )
    password = forms.CharField(
        label=_('Password'), strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Set a password'}),
    )
    confirm_password = forms.CharField(
        label=_('Confirm Password'), strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password'}),
    )

    # Parent fields
    relationship = forms.ChoiceField(
        choices=Parent.RELATIONSHIP_CHOICES,
        label=_('Relationship to Student'),
    )
    occupation = forms.CharField(
        max_length=100, required=False, label=_('Occupation'),
        widget=forms.TextInput(attrs={'placeholder': 'Occupation'}),
    )
    office_address = forms.CharField(
        required=False, label=_('Office Address'),
        widget=forms.Textarea(attrs={'rows': 2}),
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

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', _('Passwords do not match.'))
        return cleaned


class ParentForm(forms.ModelForm):
    """Update an existing Parent's profile (not the linked User)."""

    class Meta:
        model = Parent
        fields = ['relationship', 'occupation', 'office_address']
        widgets = {
            'relationship': forms.Select(),
            'occupation': forms.TextInput(attrs={'placeholder': 'Occupation'}),
            'office_address': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'relationship': _('Relationship'),
            'occupation': _('Occupation'),
            'office_address': _('Office Address'),
        }


class ParentLinkStudentForm(forms.Form):
    """Link a parent to one or more students."""

    students = forms.ModelMultipleChoiceField(
        queryset=Student.objects.select_related('user').order_by('admission_number'),
        widget=forms.CheckboxSelectMultiple,
        label=_('Students to Link'),
        required=False,
    )


# ─── Medical Info Form ─────────────────────────────────────────────────────────

class MedicalInfoForm(forms.ModelForm):
    """Create or update MedicalInfo for a student."""

    class Meta:
        model = MedicalInfo
        fields = [
            'blood_group',
            'genotype',
            'allergies',
            'medical_conditions',
            'medications',
            'emergency_contact_name',
            'emergency_contact_phone',
            'doctor_name',
            'doctor_phone',
        ]
        widgets = {
            'blood_group': forms.Select(),
            'genotype': forms.TextInput(attrs={'placeholder': 'e.g. AA, AS, SS'}),
            'allergies': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'List any known allergies…',
            }),
            'medical_conditions': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Known medical conditions…',
            }),
            'medications': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Current medications…',
            }),
            'emergency_contact_name': forms.TextInput(attrs={'placeholder': 'Full name'}),
            'emergency_contact_phone': forms.TextInput(attrs={'placeholder': '+234…'}),
            'doctor_name': forms.TextInput(attrs={'placeholder': "Doctor's full name"}),
            'doctor_phone': forms.TextInput(attrs={'placeholder': "+234…"}),
        }
        labels = {
            'blood_group': _('Blood Group'),
            'genotype': _('Genotype'),
            'allergies': _('Allergies'),
            'medical_conditions': _('Medical Conditions'),
            'medications': _('Medications'),
            'emergency_contact_name': _('Emergency Contact Name'),
            'emergency_contact_phone': _('Emergency Contact Phone'),
            'doctor_name': _("Doctor's Name"),
            'doctor_phone': _("Doctor's Phone"),
        }


# ─── Document Form ─────────────────────────────────────────────────────────────

class StudentDocumentForm(forms.ModelForm):
    """Upload a document for a student."""

    class Meta:
        model = StudentDocument
        fields = ['doc_type', 'title', 'file']
        widgets = {
            'doc_type': forms.Select(),
            'title': forms.TextInput(attrs={'placeholder': 'Document title'}),
            'file': forms.FileInput(),
        }
        labels = {
            'doc_type': _('Document Type'),
            'title': _('Title'),
            'file': _('File'),
        }

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if f and hasattr(f, 'size'):
            max_size = 10 * 1024 * 1024  # 10 MB
            if f.size > max_size:
                raise ValidationError(_('File must be smaller than 10 MB.'))
        return f


# ─── Promotion Form ────────────────────────────────────────────────────────────

class StudentPromotionForm(forms.Form):
    """
    Bulk-promote a selection of students from one ClassArm to another
    within a given academic session.
    """

    from_class = forms.ModelChoiceField(
        queryset=ClassArm.objects.none(),
        label=_('From Class'),
        empty_label='— Select Source Class —',
    )
    to_class = forms.ModelChoiceField(
        queryset=ClassArm.objects.none(),
        label=_('To Class'),
        empty_label='— Select Destination Class —',
    )
    session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.order_by('-start_date'),
        label=_('Academic Session'),
        empty_label='— Select Session —',
    )
    students = forms.ModelMultipleChoiceField(
        queryset=Student.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label=_('Students to Promote'),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = _class_arm_queryset()
        self.fields['from_class'].queryset = qs
        self.fields['to_class'].queryset = qs
        self.fields['students'].queryset = (
            Student.objects.filter(status=StudentStatus.ACTIVE)
            .select_related('user', 'class_enrolled__class_level')
            .order_by('admission_number')
        )

    def clean(self):
        cleaned = super().clean()
        from_cls = cleaned.get('from_class')
        to_cls = cleaned.get('to_class')
        if from_cls and to_cls and from_cls == to_cls:
            raise ValidationError(_('Source and destination classes must be different.'))
        return cleaned
