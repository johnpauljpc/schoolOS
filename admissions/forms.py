"""
admissions/forms.py

Forms for the admissions workflow:
  - ApplicantForm          – public application form
  - ApplicantReviewForm    – admission officer review
  - AdmissionForm          – confirm enrolment after admission
"""

from django import forms
from .models import Applicant, Admission
from academics.models import ClassLevel, AcademicSession


# ─── ApplicantForm ────────────────────────────────────────────────────────────

class ApplicantForm(forms.ModelForm):
    """
    Full public application form — no authentication required.
    Covers all Applicant fields except system-managed ones
    (application_number, status, reviewed_by, review_notes, review_date).
    """

    class Meta:
        model = Applicant
        fields = [
            # Personal info
            'first_name', 'last_name', 'middle_name',
            'date_of_birth', 'gender', 'religion',
            'nationality', 'state_of_origin', 'lga',
            # Academic
            'applying_for_class', 'session',
            'previous_school', 'previous_class',
            # Guardian info
            'guardian_name', 'guardian_relationship',
            'guardian_phone', 'guardian_email', 'guardian_address',
            # Photo
            'passport_photo',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Last Name'
            }),
            'middle_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Middle Name (optional)'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'religion': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Christianity, Islam'
            }),
            'nationality': forms.TextInput(attrs={'class': 'form-control'}),
            'state_of_origin': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'State of Origin'
            }),
            'lga': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Local Government Area'
            }),
            'applying_for_class': forms.Select(attrs={'class': 'form-control'}),
            'session': forms.Select(attrs={'class': 'form-control'}),
            'previous_school': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Previous School Name'
            }),
            'previous_class': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. JSS2, Primary 6'
            }),
            'guardian_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Full Name of Guardian'
            }),
            'guardian_relationship': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Father, Mother'
            }),
            'guardian_phone': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': '+234 ...'
            }),
            'guardian_email': forms.EmailInput(attrs={
                'class': 'form-control', 'placeholder': 'guardian@email.com'
            }),
            'guardian_address': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Guardian home/office address'
            }),
            'passport_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show only current/future sessions
        self.fields['session'].queryset = AcademicSession.objects.order_by('-start_date')
        self.fields['applying_for_class'].queryset = ClassLevel.objects.all()
        # Required fields
        self.fields['guardian_name'].required = True
        self.fields['guardian_relationship'].required = True
        self.fields['guardian_phone'].required = True


# ─── ApplicantReviewForm ─────────────────────────────────────────────────────

class ApplicantReviewForm(forms.ModelForm):
    """
    Used by admission officers to screen / admit / reject an applicant.
    """
    STATUS_CHOICES = [
        ('SCREENED', 'Screened'),
        ('ADMITTED', 'Admitted'),
        ('REJECTED', 'Rejected'),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Decision',
    )
    review_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 4,
            'placeholder': 'Optional review notes or reason for rejection...'
        }),
        label='Review Notes',
    )

    class Meta:
        model = Applicant
        fields = ['status', 'review_notes']


# ─── AdmissionForm ────────────────────────────────────────────────────────────

class AdmissionForm(forms.ModelForm):
    """
    Used to record the final admission and link to an existing / new student.
    This form is presented only after an applicant's status is ADMITTED.
    """

    class Meta:
        model = Admission
        fields = ['student', 'admission_letter_generated']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-control'}),
            'admission_letter_generated': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'student': 'Link to Existing Student (leave blank to auto-create)',
            'admission_letter_generated': 'Mark admission letter as generated',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].required = False
