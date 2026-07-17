"""
academics/forms.py

ModelForms for all academics models.
"""

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import (
    AcademicSession,
    AcademicTerm,
    ClassArm,
    ClassLevel,
    ClassTeacherAssignment,
    Department,
    Subject,
    SubjectAssignment,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Common widget helpers
# ---------------------------------------------------------------------------

TEXT_INPUT  = forms.TextInput(attrs={'class': 'form-control'})
DATE_INPUT  = forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
SELECT      = forms.Select(attrs={'class': 'form-control'})
CHECKBOX    = forms.CheckboxInput(attrs={'class': 'form-check-input'})
TEXTAREA    = forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
NUMBER      = forms.NumberInput(attrs={'class': 'form-control'})
M2M_SELECT  = forms.SelectMultiple(attrs={'class': 'form-control', 'size': 6})


# ---------------------------------------------------------------------------
# AcademicSessionForm
# ---------------------------------------------------------------------------

class AcademicSessionForm(forms.ModelForm):
    class Meta:
        model  = AcademicSession
        fields = ['name', 'start_date', 'end_date', 'is_current']
        widgets = {
            'name':       TEXT_INPUT,
            'start_date': DATE_INPUT,
            'end_date':   DATE_INPUT,
            'is_current': CHECKBOX,
        }
        labels = {
            'name':       'Session Name (e.g. 2024/2025)',
            'is_current': 'Set as Current Session',
        }

    def clean(self):
        cleaned = super().clean()
        start   = cleaned.get('start_date')
        end     = cleaned.get('end_date')
        if start and end and end <= start:
            raise forms.ValidationError('End date must be after start date.')
        return cleaned


# ---------------------------------------------------------------------------
# AcademicTermForm
# ---------------------------------------------------------------------------

class AcademicTermForm(forms.ModelForm):
    class Meta:
        model  = AcademicTerm
        fields = ['session', 'name', 'start_date', 'end_date', 'is_current', 'next_term_begins']
        widgets = {
            'session':          SELECT,
            'name':             SELECT,
            'start_date':       DATE_INPUT,
            'end_date':         DATE_INPUT,
            'is_current':       CHECKBOX,
            'next_term_begins': DATE_INPUT,
        }
        labels = {
            'is_current': 'Set as Current Term',
        }

    def clean(self):
        cleaned = super().clean()
        start   = cleaned.get('start_date')
        end     = cleaned.get('end_date')
        ntb     = cleaned.get('next_term_begins')
        if start and end and end <= start:
            raise forms.ValidationError('End date must be after start date.')
        if ntb and end and ntb <= end:
            raise forms.ValidationError('Next term begins date must be after the end date.')
        return cleaned


# ---------------------------------------------------------------------------
# DepartmentForm
# ---------------------------------------------------------------------------

class DepartmentForm(forms.ModelForm):
    class Meta:
        model  = Department
        fields = ['name', 'description', 'head']
        widgets = {
            'name':        TEXT_INPUT,
            'description': TEXTAREA,
            'head':        SELECT,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show staff users as potential department heads
        self.fields['head'].queryset = User.objects.filter(
            is_active=True,
            role__in=['SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'VICE_PRINCIPAL',
                      'TEACHER', 'CLASS_TEACHER'],
        ).order_by('last_name', 'first_name')
        self.fields['head'].empty_label = '— No Head Assigned —'


# ---------------------------------------------------------------------------
# ClassLevelForm
# ---------------------------------------------------------------------------

class ClassLevelForm(forms.ModelForm):
    class Meta:
        model  = ClassLevel
        fields = ['name', 'order', 'section']
        widgets = {
            'name':    TEXT_INPUT,
            'order':   NUMBER,
            'section': SELECT,
        }
        help_texts = {
            'order':   'Lower numbers sort first. e.g. JSS1=1, JSS2=2 … SS3=6',
        }


# ---------------------------------------------------------------------------
# ClassArmForm
# ---------------------------------------------------------------------------

class ClassArmForm(forms.ModelForm):
    class Meta:
        model  = ClassArm
        fields = ['class_level', 'name', 'capacity']
        widgets = {
            'class_level': SELECT,
            'name':        TEXT_INPUT,
            'capacity':    NUMBER,
        }


# ---------------------------------------------------------------------------
# SubjectForm
# ---------------------------------------------------------------------------

class SubjectForm(forms.ModelForm):
    class Meta:
        model  = Subject
        fields = ['name', 'code', 'department', 'class_levels', 'is_compulsory', 'description']
        widgets = {
            'name':         TEXT_INPUT,
            'code':         TEXT_INPUT,
            'department':   SELECT,
            'class_levels': M2M_SELECT,
            'is_compulsory': CHECKBOX,
            'description':  TEXTAREA,
        }
        labels = {
            'class_levels': 'Applicable Class Levels (hold Ctrl/⌘ to multi-select)',
        }


# ---------------------------------------------------------------------------
# SubjectAssignmentForm
# ---------------------------------------------------------------------------

class SubjectAssignmentForm(forms.ModelForm):
    class Meta:
        model  = SubjectAssignment
        fields = ['teacher', 'subject', 'class_arm', 'session', 'term']
        widgets = {
            'teacher':   SELECT,
            'subject':   SELECT,
            'class_arm': SELECT,
            'session':   SELECT,
            'term':      SELECT,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].queryset = User.objects.filter(
            role__in=['TEACHER', 'CLASS_TEACHER'],
            is_active=True,
        ).order_by('last_name', 'first_name')
        self.fields['teacher'].empty_label = '— Select Teacher —'
        self.fields['subject'].empty_label = '— Select Subject —'
        self.fields['class_arm'].empty_label = '— Select Class Arm —'
        self.fields['session'].empty_label = '— Select Session —'
        self.fields['term'].empty_label = '— Select Term —'


# ---------------------------------------------------------------------------
# ClassTeacherAssignmentForm
# ---------------------------------------------------------------------------

class ClassTeacherAssignmentForm(forms.ModelForm):
    class Meta:
        model  = ClassTeacherAssignment
        fields = ['teacher', 'class_arm', 'session']
        widgets = {
            'teacher':   SELECT,
            'class_arm': SELECT,
            'session':   SELECT,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].queryset = User.objects.filter(
            is_active=True,
        ).order_by('last_name', 'first_name')
        self.fields['teacher'].empty_label = '— Select Class Teacher —'
        self.fields['class_arm'].empty_label = '— Select Class Arm —'
        self.fields['session'].empty_label = '— Select Session —'
