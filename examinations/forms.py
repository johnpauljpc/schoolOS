"""
examinations/forms.py

All forms for the examinations workflow:
  - GradeConfigForm
  - AssessmentEntryForm / AssessmentBulkForm (formset)
  - ExamScoreEntryForm  / ExamScoreBulkForm  (formset)
  - ResultFilterForm
  - ExamTimetableForm
  - ClassTimetableForm
"""

from django import forms
from django.forms import BaseFormSet, formset_factory

from academics.models import AcademicSession, AcademicTerm, ClassArm, Subject
from students.models import Student

from .models import (
    Assessment,
    ClassTimetable,
    ExaminationScore,
    ExaminationTimetable,
    GradeConfig,
    Result,
)


# ─── GradeConfigForm ──────────────────────────────────────────────────────────

class GradeConfigForm(forms.ModelForm):
    """Create / update a grade boundary configuration."""

    class Meta:
        model = GradeConfig
        fields = ['min_score', 'max_score', 'grade', 'remark', 'point', 'is_pass']
        widgets = {
            'min_score': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'max': 100
            }),
            'max_score': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'max': 100
            }),
            'grade': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. A1, B2, F9'
            }),
            'remark': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Excellent, Pass, Fail'
            }),
            'point': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': 0
            }),
            'is_pass': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'min_score': 'Minimum Score',
            'max_score': 'Maximum Score',
            'grade': 'Grade Symbol',
            'remark': 'Remark',
            'point': 'Grade Points',
            'is_pass': 'Is a Passing Grade?',
        }

    def clean(self):
        cleaned_data = super().clean()
        min_score = cleaned_data.get('min_score')
        max_score = cleaned_data.get('max_score')
        if min_score is not None and max_score is not None:
            if min_score > max_score:
                raise forms.ValidationError(
                    'Minimum score cannot be greater than maximum score.'
                )
        return cleaned_data


# ─── AssessmentEntryForm ──────────────────────────────────────────────────────

class AssessmentEntryForm(forms.ModelForm):
    """
    Enter CA scores (CA1, CA2, CA3) for a single student.
    Hidden fields carry student identity; only score fields are user-editable.
    """
    student_id = forms.IntegerField(widget=forms.HiddenInput())
    student_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-plaintext', 'readonly': True
        }),
    )

    class Meta:
        model = Assessment
        fields = ['ca1', 'ca2', 'ca3']
        widgets = {
            'ca1': forms.NumberInput(attrs={
                'class': 'form-control score-input',
                'min': 0, 'max': 20, 'step': '0.5',
                'placeholder': '0'
            }),
            'ca2': forms.NumberInput(attrs={
                'class': 'form-control score-input',
                'min': 0, 'max': 20, 'step': '0.5',
                'placeholder': '0'
            }),
            'ca3': forms.NumberInput(attrs={
                'class': 'form-control score-input',
                'min': 0, 'max': 20, 'step': '0.5',
                'placeholder': '0'
            }),
        }

    def clean_ca1(self):
        val = self.cleaned_data.get('ca1', 0)
        if val is not None and (val < 0 or val > 20):
            raise forms.ValidationError('CA1 must be between 0 and 20.')
        return val

    def clean_ca2(self):
        val = self.cleaned_data.get('ca2', 0)
        if val is not None and (val < 0 or val > 20):
            raise forms.ValidationError('CA2 must be between 0 and 20.')
        return val

    def clean_ca3(self):
        val = self.cleaned_data.get('ca3', 0)
        if val is not None and (val < 0 or val > 20):
            raise forms.ValidationError('CA3 must be between 0 and 20.')
        return val


class BaseAssessmentFormSet(BaseFormSet):
    """Custom formset that validates the whole CA batch."""

    def clean(self):
        if any(self.errors):
            return
        # Optionally add cross-form validation here


# Create a formset factory for CA bulk entry
AssessmentBulkForm = formset_factory(
    AssessmentEntryForm,
    formset=BaseAssessmentFormSet,
    extra=0,
    can_delete=False,
)


# ─── ExamScoreEntryForm ───────────────────────────────────────────────────────

class ExamScoreEntryForm(forms.ModelForm):
    """Enter exam score (out of 60) for a single student."""

    student_id = forms.IntegerField(widget=forms.HiddenInput())
    student_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-plaintext', 'readonly': True
        }),
    )

    class Meta:
        model = ExaminationScore
        fields = ['score']
        widgets = {
            'score': forms.NumberInput(attrs={
                'class': 'form-control score-input',
                'min': 0, 'max': 60, 'step': '0.5',
                'placeholder': '0'
            }),
        }

    def clean_score(self):
        val = self.cleaned_data.get('score', 0)
        if val is not None and (val < 0 or val > 60):
            raise forms.ValidationError('Exam score must be between 0 and 60.')
        return val


class BaseExamScoreFormSet(BaseFormSet):
    """Custom formset for exam score bulk entry."""

    def clean(self):
        if any(self.errors):
            return


ExamScoreBulkForm = formset_factory(
    ExamScoreEntryForm,
    formset=BaseExamScoreFormSet,
    extra=0,
    can_delete=False,
)


# ─── ResultFilterForm ─────────────────────────────────────────────────────────

class ResultFilterForm(forms.Form):
    """
    Filter results by session, term, and class_arm.
    All fields are optional to allow partial filtering.
    """
    session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.order_by('-start_date'),
        required=False,
        empty_label='— All Sessions —',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    term = forms.ModelChoiceField(
        queryset=AcademicTerm.objects.select_related('session').order_by('-session__start_date', 'name'),
        required=False,
        empty_label='— All Terms —',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    class_arm = forms.ModelChoiceField(
        queryset=ClassArm.objects.select_related('class_level').order_by('class_level__order', 'name'),
        required=False,
        empty_label='— All Classes —',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )


# ─── ExamTimetableForm ────────────────────────────────────────────────────────

class ExamTimetableForm(forms.ModelForm):
    """Schedule an examination slot."""

    class Meta:
        model = ExaminationTimetable
        fields = ['subject', 'class_arm', 'session', 'term', 'exam_date',
                  'start_time', 'end_time', 'venue']
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'class_arm': forms.Select(attrs={'class': 'form-control'}),
            'session': forms.Select(attrs={'class': 'form-control'}),
            'term': forms.Select(attrs={'class': 'form-control'}),
            'exam_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'venue': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Hall A, Room 12'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('Start time must be before end time.')
        return cleaned_data


# ─── ClassTimetableForm ───────────────────────────────────────────────────────

class ClassTimetableForm(forms.ModelForm):
    """Create or edit a weekly class timetable slot."""

    class Meta:
        model = ClassTimetable
        fields = ['class_arm', 'subject', 'teacher', 'session', 'term',
                  'day_of_week', 'start_time', 'end_time']
        widgets = {
            'class_arm': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'teacher': forms.Select(attrs={'class': 'form-control'}),
            'session': forms.Select(attrs={'class': 'form-control'}),
            'term': forms.Select(attrs={'class': 'form-control'}),
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User, Role
        self.fields['teacher'].queryset = User.objects.filter(
            role__in=[Role.TEACHER, Role.CLASS_TEACHER],
            is_active=True,
        ).order_by('last_name', 'first_name')
        self.fields['teacher'].required = False

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('Start time must be before end time.')
        return cleaned_data
