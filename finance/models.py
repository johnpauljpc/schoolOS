import uuid
from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class FeeCategory(TimeStampedModel):
    """Types of fees: Tuition, Development Levy, Sports, etc."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Fee Category'
        verbose_name_plural = 'Fee Categories'

    def __str__(self):
        return self.name


class FeeStructure(TimeStampedModel):
    """Amount per fee category per class per session/term."""
    category = models.ForeignKey(FeeCategory, on_delete=models.CASCADE, related_name='structures')
    class_level = models.ForeignKey('academics.ClassLevel', on_delete=models.CASCADE)
    session = models.ForeignKey('academics.AcademicSession', on_delete=models.CASCADE)
    term = models.ForeignKey('academics.AcademicTerm', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_compulsory = models.BooleanField(default=True)

    class Meta:
        unique_together = ('category', 'class_level', 'session', 'term')
        ordering = ['class_level__order', 'category__name']
        verbose_name = 'Fee Structure'
        verbose_name_plural = 'Fee Structures'

    def __str__(self):
        return f"{self.category} — {self.class_level} — {self.session}/{self.term}: ₦{self.amount:,.2f}"


class Invoice(TimeStampedModel):
    """An invoice issued to a student for a session/term."""
    STATUS_CHOICES = [
        ('UNPAID', 'Unpaid'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]
    invoice_number = models.CharField(max_length=30, unique=True)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='invoices')
    session = models.ForeignKey('academics.AcademicSession', on_delete=models.CASCADE)
    term = models.ForeignKey('academics.AcademicTerm', on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='UNPAID')
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'

    def __str__(self):
        return f"{self.invoice_number} — {self.student} — {self.status}"

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    def update_status(self):
        if self.amount_paid <= 0:
            self.status = 'UNPAID'
        elif self.amount_paid < self.total_amount:
            self.status = 'PARTIAL'
        else:
            self.status = 'PAID'
        self.save(update_fields=['status'])


class InvoiceItem(models.Model):
    """Line items on an invoice."""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.description}: ₦{self.amount:,.2f}"


class Payment(TimeStampedModel):
    """A payment record against an invoice."""
    PAYMENT_METHOD_CHOICES = [
        ('ONLINE', 'Online (Paystack)'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CASH', 'Cash'),
        ('POS', 'POS Terminal'),
        ('CHEQUE', 'Cheque'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Successful'),
        ('FAILED', 'Failed'),
        ('REVERSED', 'Reversed'),
    ]
    payment_reference = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='SUCCESS')
    narration = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recorded_payments'
    )
    # Bank-specific fields
    bank_name = models.CharField(max_length=100, blank=True)
    cheque_number = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f"{self.payment_reference} — ₦{self.amount_paid:,.2f} — {self.get_payment_method_display()}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update invoice totals
        invoice = self.invoice
        successful = invoice.payments.filter(status='SUCCESS').aggregate(
            total=models.Sum('amount_paid')
        )['total'] or 0
        invoice.amount_paid = successful
        invoice.save(update_fields=['amount_paid'])
        invoice.update_status()


class PaymentTransaction(models.Model):
    """Raw Paystack transaction data for online payments."""
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='transaction')
    gateway = models.CharField(max_length=20, default='PAYSTACK')
    gateway_reference = models.CharField(max_length=200, blank=True)  # Paystack trxref
    paystack_id = models.CharField(max_length=50, blank=True)
    authorization_code = models.CharField(max_length=100, blank=True)
    channel = models.CharField(max_length=50, blank=True)  # card, bank, ussd
    currency = models.CharField(max_length=5, default='NGN')
    gateway_status = models.CharField(max_length=20, blank=True)
    raw_response = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'

    def __str__(self):
        return f"Paystack: {self.gateway_reference} — {self.gateway_status}"


class Receipt(TimeStampedModel):
    """Auto-generated receipt for a successful payment."""
    receipt_number = models.CharField(max_length=30, unique=True)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='receipt')
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']
        verbose_name = 'Receipt'
        verbose_name_plural = 'Receipts'

    def __str__(self):
        return f"Receipt #{self.receipt_number}"
