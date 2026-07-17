"""
finance/forms.py

Forms for the SchoolOS Finance module.
"""
from django import forms
from django.utils import timezone

from academics.models import AcademicSession, AcademicTerm, ClassLevel
from .models import FeeCategory, FeeStructure, Invoice, Payment


class FeeCategoryForm(forms.ModelForm):
    """Create / edit a FeeCategory."""

    class Meta:
        model = FeeCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Tuition Fee'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FeeStructureForm(forms.ModelForm):
    """Create / edit a FeeStructure (amount per category per class/term)."""

    class Meta:
        model = FeeStructure
        fields = ['category', 'class_level', 'session', 'term', 'amount', 'is_compulsory']
        widgets = {
            'category':     forms.Select(attrs={'class': 'form-control'}),
            'class_level':  forms.Select(attrs={'class': 'form-control'}),
            'session':      forms.Select(attrs={'class': 'form-control'}),
            'term':         forms.Select(attrs={'class': 'form-control'}),
            'amount':       forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'is_compulsory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = FeeCategory.objects.filter(is_active=True)
        self.fields['class_level'].queryset = ClassLevel.objects.all()
        self.fields['session'].queryset = AcademicSession.objects.all()
        self.fields['term'].queryset = AcademicTerm.objects.select_related('session').all()


class InvoiceGenerateForm(forms.Form):
    """
    Bulk-generate invoices for all active students in a class.
    Accountants select a session, term, and class level; the view
    creates one Invoice (with InvoiceItems) per student.
    """
    session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='— Select Session —',
    )
    term = forms.ModelChoiceField(
        queryset=AcademicTerm.objects.select_related('session').all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='— Select Term —',
    )
    class_level = forms.ModelChoiceField(
        queryset=ClassLevel.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='— Select Class Level —',
    )
    due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text='Optional: deadline for payment.',
    )

    def clean(self):
        cleaned = super().clean()
        session = cleaned.get('session')
        term = cleaned.get('term')
        if session and term and term.session != session:
            raise forms.ValidationError('The selected term does not belong to the selected session.')
        return cleaned


class ManualPaymentForm(forms.Form):
    """
    Record an offline (non-Paystack) payment against an invoice.
    The ONLINE method is excluded — those go through Paystack.
    """
    OFFLINE_METHOD_CHOICES = [
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CASH',          'Cash'),
        ('POS',           'POS Terminal'),
        ('CHEQUE',        'Cheque'),
    ]

    invoice = forms.ModelChoiceField(
        queryset=Invoice.objects.select_related('student__user').exclude(status='CANCELLED'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='— Select Invoice —',
    )
    amount_paid = forms.DecimalField(
        max_digits=12, decimal_places=2,
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    payment_method = forms.ChoiceField(
        choices=OFFLINE_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    payment_date = forms.DateField(
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    narration = forms.CharField(
        required=False, max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional note'}),
    )
    bank_name = forms.CharField(
        required=False, max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bank name (for transfer/cheque)'}),
    )
    cheque_number = forms.CharField(
        required=False, max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cheque number if applicable'}),
    )

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get('payment_method')
        if method == 'CHEQUE' and not cleaned.get('cheque_number'):
            self.add_error('cheque_number', 'Cheque number is required for cheque payments.')
        return cleaned


class FinanceReportFilterForm(forms.Form):
    """Filter form used on revenue and outstanding-fees reports."""

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='From Date',
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='To Date',
    )
    session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.all(),
        required=False,
        empty_label='All Sessions',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    term = forms.ModelChoiceField(
        queryset=AcademicTerm.objects.select_related('session').all(),
        required=False,
        empty_label='All Terms',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    class_level = forms.ModelChoiceField(
        queryset=ClassLevel.objects.all(),
        required=False,
        empty_label='All Classes',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
