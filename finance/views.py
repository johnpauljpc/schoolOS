"""
finance/views.py

All views for the SchoolOS Finance module.

Roles used:
  - ACCOUNTANT / PRINCIPAL / SUPER_ADMIN / ICT_ADMIN : admin-facing finance ops
  - STUDENT / PARENT : can view their own invoices / make online payments
"""
import hashlib
import hmac
import json
import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from academics.models import AcademicSession, AcademicTerm, ClassLevel
from communication.models import Notification
from core.decorators import role_required, staff_required
from core.utils import (
    auto_fit_columns,
    create_excel_workbook,
    excel_response,
    generate_pdf_response,
    paginate_queryset,
    style_data_row,
    style_header_row,
)
from students.models import Student

from .forms import (
    FeeCategoryForm,
    FeeStructureForm,
    FinanceReportFilterForm,
    InvoiceGenerateForm,
    ManualPaymentForm,
)
from .models import (
    FeeCategory,
    FeeStructure,
    Invoice,
    InvoiceItem,
    Payment,
    PaymentTransaction,
    Receipt,
)
from .paystack import PaystackAPI, PaystackAPIError

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _generate_receipt_number() -> str:
    """Generate a sequential receipt number like RCP-2024-0001."""
    year = timezone.now().year
    last = Receipt.objects.filter(receipt_number__startswith=f'RCP-{year}-').order_by('-receipt_number').first()
    if last:
        try:
            seq = int(last.receipt_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f'RCP-{year}-{seq:04d}'


def _generate_invoice_number() -> str:
    """Generate a sequential invoice number like INV-2024-0001."""
    year = timezone.now().year
    last = Invoice.objects.filter(invoice_number__startswith=f'INV-{year}-').order_by('-invoice_number').first()
    if last:
        try:
            seq = int(last.invoice_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f'INV-{year}-{seq:04d}'


def _create_receipt_for_payment(payment: Payment) -> Receipt:
    """Create a Receipt record for a successful Payment."""
    receipt = Receipt.objects.create(
        receipt_number=_generate_receipt_number(),
        payment=payment,
    )
    return receipt


def _notify_student_payment(student: Student, payment: Payment, receipt: Receipt) -> None:
    """Send a portal notification to the student (and parent users if linked)."""
    link = reverse('finance:receipt_detail', kwargs={'pk': receipt.pk})
    msg = (
        f'Payment of ₦{payment.amount_paid:,.2f} received for invoice '
        f'{payment.invoice.invoice_number}. Receipt: {receipt.receipt_number}.'
    )
    Notification.send(
        user=student.user,
        title='Payment Confirmed',
        message=msg,
        notification_type='PAYMENT',
        link=link,
    )
    # Notify parent users if any
    for parent in student.parents.select_related('user'):
        Notification.send(
            user=parent.user,
            title='Payment Confirmed',
            message=msg,
            notification_type='PAYMENT',
            link=link,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Fee Categories
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT')
def fee_category_list(request):
    """List all fee categories."""
    categories = FeeCategory.objects.all()
    return render(request, 'finance/fee_category_list.html', {
        'title': 'Fee Categories',
        'categories': categories,
    })


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT')
def fee_category_create(request):
    """Create a new fee category."""
    form = FeeCategoryForm(request.POST or None)
    if form.is_valid():
        cat = form.save()
        messages.success(request, f'Fee category "{cat.name}" created.')
        return redirect('finance:fee_category_list')
    return render(request, 'finance/fee_category_form.html', {
        'title': 'Add Fee Category',
        'form': form,
    })


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT')
def fee_category_update(request, pk):
    """Edit an existing fee category."""
    cat = get_object_or_404(FeeCategory, pk=pk)
    form = FeeCategoryForm(request.POST or None, instance=cat)
    if form.is_valid():
        form.save()
        messages.success(request, f'Fee category "{cat.name}" updated.')
        return redirect('finance:fee_category_list')
    return render(request, 'finance/fee_category_form.html', {
        'title': f'Edit Fee Category — {cat.name}',
        'form': form,
        'object': cat,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Fee Structures
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT')
def fee_structure_list(request):
    """List fee structures with optional filters."""
    qs = FeeStructure.objects.select_related('category', 'class_level', 'session', 'term')

    session_id = request.GET.get('session')
    term_id = request.GET.get('term')
    class_id = request.GET.get('class_level')

    if session_id:
        qs = qs.filter(session_id=session_id)
    if term_id:
        qs = qs.filter(term_id=term_id)
    if class_id:
        qs = qs.filter(class_level_id=class_id)

    return render(request, 'finance/fee_structure_list.html', {
        'title': 'Fee Structures',
        'structures': qs,
        'sessions': AcademicSession.objects.all(),
        'terms': AcademicTerm.objects.select_related('session').all(),
        'class_levels': ClassLevel.objects.all(),
        'filter_session': session_id,
        'filter_term': term_id,
        'filter_class': class_id,
    })


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT')
def fee_structure_create(request):
    """Create a new fee structure entry."""
    form = FeeStructureForm(request.POST or None)
    if form.is_valid():
        fs = form.save()
        messages.success(request, f'Fee structure created: {fs}')
        return redirect('finance:fee_structure_list')
    return render(request, 'finance/fee_structure_form.html', {
        'title': 'Add Fee Structure',
        'form': form,
    })


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT')
def fee_structure_update(request, pk):
    """Edit an existing fee structure."""
    fs = get_object_or_404(FeeStructure, pk=pk)
    form = FeeStructureForm(request.POST or None, instance=fs)
    if form.is_valid():
        form.save()
        messages.success(request, 'Fee structure updated.')
        return redirect('finance:fee_structure_list')
    return render(request, 'finance/fee_structure_form.html', {
        'title': 'Edit Fee Structure',
        'form': form,
        'object': fs,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Invoices
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def invoice_list_view(request):
    """
    List invoices.

    - Staff see all invoices and can filter.
    - Students see only their own invoices.
    - Parents see invoices for their linked students.
    """
    user = request.user
    qs = Invoice.objects.select_related('student__user', 'session', 'term')

    if user.role == 'STUDENT':
        try:
            qs = qs.filter(student=user.student_profile)
        except Student.DoesNotExist:
            qs = qs.none()
    elif user.role == 'PARENT':
        try:
            student_ids = user.parent_profile.students.values_list('id', flat=True)
            qs = qs.filter(student_id__in=student_ids)
        except Exception:
            qs = qs.none()
    else:
        # Staff filters
        student_q = request.GET.get('student', '').strip()
        session_id = request.GET.get('session', '')
        term_id = request.GET.get('term', '')
        status = request.GET.get('status', '')
        class_id = request.GET.get('class_level', '')

        if student_q:
            qs = qs.filter(
                Q(student__user__first_name__icontains=student_q) |
                Q(student__user__last_name__icontains=student_q) |
                Q(student__admission_number__icontains=student_q) |
                Q(invoice_number__icontains=student_q)
            )
        if session_id:
            qs = qs.filter(session_id=session_id)
        if term_id:
            qs = qs.filter(term_id=term_id)
        if status:
            qs = qs.filter(status=status)
        if class_id:
            qs = qs.filter(student__class_enrolled__class_level_id=class_id)

    page_obj = paginate_queryset(qs, request, per_page=25)

    return render(request, 'finance/invoice_list.html', {
        'title': 'Invoices',
        'page_obj': page_obj,
        'sessions': AcademicSession.objects.all(),
        'terms': AcademicTerm.objects.select_related('session').all(),
        'class_levels': ClassLevel.objects.all(),
        'status_choices': Invoice.STATUS_CHOICES,
        'request': request,
    })


@login_required
def invoice_detail_view(request, pk):
    """Show invoice details with line items and payments."""
    invoice = get_object_or_404(
        Invoice.objects.select_related('student__user', 'session', 'term', 'generated_by'),
        pk=pk
    )
    user = request.user
    # Access control
    if user.role == 'STUDENT':
        if not hasattr(user, 'student_profile') or user.student_profile != invoice.student:
            messages.error(request, 'Access denied.')
            return redirect('finance:invoice_list')
    elif user.role == 'PARENT':
        try:
            if invoice.student not in user.parent_profile.students.all():
                messages.error(request, 'Access denied.')
                return redirect('finance:invoice_list')
        except Exception:
            messages.error(request, 'Access denied.')
            return redirect('finance:invoice_list')

    items = invoice.items.select_related('fee_structure__category')
    payments = invoice.payments.select_related('recorded_by').prefetch_related('receipt')
    paystack_public_key = settings.PAYSTACK_PUBLIC_KEY

    return render(request, 'finance/invoice_detail.html', {
        'title': f'Invoice {invoice.invoice_number}',
        'invoice': invoice,
        'items': items,
        'payments': payments,
        'paystack_public_key': paystack_public_key,
    })


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT')
def generate_invoices_view(request):
    """
    Bulk-generate invoices for all active students in a given class/session/term.
    Skips students who already have an invoice for that session/term.
    """
    form = InvoiceGenerateForm(request.POST or None)
    if form.is_valid():
        session = form.cleaned_data['session']
        term = form.cleaned_data['term']
        class_level = form.cleaned_data['class_level']
        due_date = form.cleaned_data.get('due_date')

        # Get fee structures for this combination
        fee_structures = FeeStructure.objects.filter(
            session=session, term=term, class_level=class_level
        ).select_related('category')

        if not fee_structures.exists():
            messages.warning(request, 'No fee structures found for that class/session/term.')
            return render(request, 'finance/generate_invoices.html', {'title': 'Generate Invoices', 'form': form})

        # Get students in this class level (via ClassArm enrollment)
        from academics.models import ClassArm
        arms = ClassArm.objects.filter(class_level=class_level)
        students = Student.objects.filter(
            class_enrolled__in=arms,
            status='ACTIVE'
        ).select_related('user')

        created_count = 0
        skipped_count = 0

        with db_transaction.atomic():
            for student in students:
                # Skip if invoice already exists
                if Invoice.objects.filter(student=student, session=session, term=term).exists():
                    skipped_count += 1
                    continue

                total = sum(fs.amount for fs in fee_structures)
                invoice = Invoice.objects.create(
                    invoice_number=_generate_invoice_number(),
                    student=student,
                    session=session,
                    term=term,
                    total_amount=total,
                    amount_paid=Decimal('0.00'),
                    status='UNPAID',
                    due_date=due_date,
                    generated_by=request.user,
                )
                for fs in fee_structures:
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        fee_structure=fs,
                        description=fs.category.name,
                        amount=fs.amount,
                    )
                created_count += 1

        messages.success(
            request,
            f'{created_count} invoices generated. {skipped_count} already existed and were skipped.'
        )
        return redirect('finance:invoice_list')

    return render(request, 'finance/generate_invoices.html', {
        'title': 'Bulk Generate Invoices',
        'form': form,
    })


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT')
def invoice_generate_single_view(request, student_pk):
    """Generate an invoice for a single student."""
    student = get_object_or_404(Student, pk=student_pk)
    form = InvoiceGenerateForm(request.POST or None)
    if form.is_valid():
        session = form.cleaned_data['session']
        term = form.cleaned_data['term']
        due_date = form.cleaned_data.get('due_date')

        # Determine class level from student's enrollment
        if not student.class_enrolled:
            messages.error(request, 'Student has no enrolled class. Cannot generate invoice.')
            return redirect('students:student_detail', pk=student.pk)

        class_level = student.class_enrolled.class_level
        fee_structures = FeeStructure.objects.filter(
            session=session, term=term, class_level=class_level
        ).select_related('category')

        if not fee_structures.exists():
            messages.warning(request, 'No fee structures found for this class/session/term.')
        elif Invoice.objects.filter(student=student, session=session, term=term).exists():
            messages.warning(request, 'Invoice already exists for this student/session/term.')
        else:
            total = sum(fs.amount for fs in fee_structures)
            with db_transaction.atomic():
                invoice = Invoice.objects.create(
                    invoice_number=_generate_invoice_number(),
                    student=student,
                    session=session,
                    term=term,
                    total_amount=total,
                    amount_paid=Decimal('0.00'),
                    status='UNPAID',
                    due_date=due_date,
                    generated_by=request.user,
                )
                for fs in fee_structures:
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        fee_structure=fs,
                        description=fs.category.name,
                        amount=fs.amount,
                    )
            messages.success(request, f'Invoice {invoice.invoice_number} generated for {student.full_name}.')
            return redirect('finance:invoice_detail', pk=invoice.pk)

    return render(request, 'finance/invoice_generate_single.html', {
        'title': f'Generate Invoice — {student.full_name}',
        'student': student,
        'form': form,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Payments — Offline
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT')
def offline_payment_view(request, invoice_pk=None):
    """
    Record a manual (offline) payment and auto-generate a receipt.
    Sends a portal notification to the student.
    """
    initial = {}
    if invoice_pk:
        invoice = get_object_or_404(Invoice, pk=invoice_pk)
        initial['invoice'] = invoice

    form = ManualPaymentForm(request.POST or None, initial=initial)
    if form.is_valid():
        invoice = form.cleaned_data['invoice']
        amount_paid = form.cleaned_data['amount_paid']
        method = form.cleaned_data['payment_method']
        pdate = form.cleaned_data['payment_date']
        narration = form.cleaned_data.get('narration', '')
        bank_name = form.cleaned_data.get('bank_name', '')
        cheque_number = form.cleaned_data.get('cheque_number', '')

        with db_transaction.atomic():
            payment = Payment.objects.create(
                payment_reference=uuid.uuid4(),
                invoice=invoice,
                amount_paid=amount_paid,
                payment_method=method,
                payment_date=pdate,
                status='SUCCESS',
                narration=narration,
                recorded_by=request.user,
                bank_name=bank_name,
                cheque_number=cheque_number,
            )
            receipt = _create_receipt_for_payment(payment)

        _notify_student_payment(invoice.student, payment, receipt)
        messages.success(request, f'Payment recorded. Receipt: {receipt.receipt_number}')
        return redirect('finance:receipt_detail', pk=receipt.pk)

    return render(request, 'finance/offline_payment.html', {
        'title': 'Record Offline Payment',
        'form': form,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Payments — Online (Paystack)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def online_payment_initiate_view(request, invoice_pk):
    """
    Initiate a Paystack payment for an invoice.
    Creates a pending Payment record then redirects to Paystack hosted page.
    """
    invoice = get_object_or_404(Invoice, pk=invoice_pk)

    # Access control: student can only pay their own invoice
    if request.user.role == 'STUDENT':
        if not hasattr(request.user, 'student_profile') or request.user.student_profile != invoice.student:
            messages.error(request, 'Access denied.')
            return redirect('finance:invoice_list')

    if invoice.status == 'PAID':
        messages.info(request, 'This invoice is already fully paid.')
        return redirect('finance:invoice_detail', pk=invoice.pk)

    balance = invoice.balance
    if balance <= 0:
        messages.info(request, 'No outstanding balance on this invoice.')
        return redirect('finance:invoice_detail', pk=invoice.pk)

    # Build a unique reference for this attempt
    ref = f'PAY-{invoice.invoice_number}-{uuid.uuid4().hex[:8].upper()}'
    callback_url = request.build_absolute_uri(reverse('finance:paystack_callback'))

    api = PaystackAPI()
    try:
        result = api.initialize_transaction(
            email=invoice.student.email,
            amount_kobo=int(balance * 100),
            reference=ref,
            callback_url=callback_url,
            metadata={
                'invoice_id': invoice.pk,
                'invoice_number': invoice.invoice_number,
                'student_name': invoice.student.full_name,
            },
        )
    except PaystackAPIError as exc:
        logger.error('Paystack init failed for invoice %s: %s', invoice.invoice_number, exc)
        messages.error(request, f'Could not initiate payment: {exc}')
        return redirect('finance:invoice_detail', pk=invoice.pk)

    # Create a PENDING payment record
    with db_transaction.atomic():
        payment = Payment.objects.create(
            payment_reference=ref,
            invoice=invoice,
            amount_paid=balance,
            payment_method='ONLINE',
            payment_date=timezone.now().date(),
            status='PENDING',
            narration='Online payment via Paystack',
            recorded_by=request.user,
        )
        PaymentTransaction.objects.create(
            payment=payment,
            gateway='PAYSTACK',
            gateway_reference=ref,
            gateway_status='pending',
            raw_response=result,
        )

    authorization_url = result['data']['authorization_url']
    return redirect(authorization_url)


@login_required
def paystack_callback_view(request):
    """
    GET callback from Paystack after the customer completes (or abandons) payment.
    Verifies the transaction and updates Payment + Invoice + creates Receipt.
    """
    reference = request.GET.get('reference') or request.GET.get('trxref')
    if not reference:
        messages.error(request, 'Invalid payment callback — no reference provided.')
        return redirect('finance:invoice_list')

    # Find the pending payment
    payment = Payment.objects.filter(payment_reference=reference, payment_method='ONLINE').first()
    if not payment:
        messages.error(request, f'Payment record not found for reference: {reference}')
        return redirect('finance:invoice_list')

    api = PaystackAPI()
    try:
        result = api.verify_transaction(reference)
    except PaystackAPIError as exc:
        logger.error('Paystack verify failed for ref %s: %s', reference, exc)
        messages.error(request, f'Could not verify payment: {exc}')
        return redirect('finance:invoice_detail', pk=payment.invoice.pk)

    gateway_data = result.get('data', {})
    gateway_status = gateway_data.get('status', 'failed')

    with db_transaction.atomic():
        # Update transaction record
        tx = PaymentTransaction.objects.filter(payment=payment).first()
        if tx:
            tx.gateway_status = gateway_status
            tx.paystack_id = str(gateway_data.get('id', ''))
            tx.authorization_code = gateway_data.get('authorization', {}).get('authorization_code', '')
            tx.channel = gateway_data.get('channel', '')
            tx.raw_response = result
            tx.save()

        if gateway_status == 'success':
            payment.status = 'SUCCESS'
            # Use Paystack-confirmed amount (in kobo → naira)
            confirmed_amount = Decimal(gateway_data.get('amount', 0)) / 100
            payment.amount_paid = confirmed_amount
            payment.save()
            invoice = payment.invoice
            invoice.amount_paid = invoice.payments.filter(status='SUCCESS').aggregate(
                total=Sum('amount_paid')
            )['total'] or Decimal('0.00')
            invoice.save(update_fields=['amount_paid'])
            invoice.update_status()
            receipt = _create_receipt_for_payment(payment)
            _notify_student_payment(invoice.student, payment, receipt)
            messages.success(request, f'Payment successful! Receipt: {receipt.receipt_number}')
            return redirect('finance:receipt_detail', pk=receipt.pk)
        else:
            payment.status = 'FAILED'
            payment.save(update_fields=['status'])
            messages.error(request, f'Payment was not successful (status: {gateway_status}). Please try again.')
            return redirect('finance:invoice_detail', pk=payment.invoice.pk)


@csrf_exempt
def paystack_webhook_view(request):
    """
    POST webhook from Paystack (server-to-server event).
    Verifies HMAC-SHA512 signature then processes charge.success events.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    paystack_signature = request.headers.get('X-Paystack-Signature', '')
    secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
    computed = hmac.new(secret, request.body, hashlib.sha512).hexdigest()

    if not hmac.compare_digest(computed, paystack_signature):
        logger.warning('Paystack webhook: invalid signature')
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    event = payload.get('event')
    data = payload.get('data', {})
    reference = data.get('reference', '')

    logger.info('Paystack webhook: event=%s ref=%s', event, reference)

    if event == 'charge.success':
        payment = Payment.objects.filter(payment_reference=reference, payment_method='ONLINE').first()
        if payment and payment.status != 'SUCCESS':
            with db_transaction.atomic():
                gateway_status = data.get('status', 'success')
                tx, _ = PaymentTransaction.objects.get_or_create(payment=payment)
                tx.gateway_status = gateway_status
                tx.paystack_id = str(data.get('id', ''))
                tx.authorization_code = data.get('authorization', {}).get('authorization_code', '')
                tx.channel = data.get('channel', '')
                tx.raw_response = payload
                tx.save()

                payment.status = 'SUCCESS'
                confirmed_amount = Decimal(data.get('amount', 0)) / 100
                payment.amount_paid = confirmed_amount
                payment.save()

                invoice = payment.invoice
                invoice.amount_paid = invoice.payments.filter(status='SUCCESS').aggregate(
                    total=Sum('amount_paid')
                )['total'] or Decimal('0.00')
                invoice.save(update_fields=['amount_paid'])
                invoice.update_status()

                if not hasattr(payment, 'receipt'):
                    receipt = _create_receipt_for_payment(payment)
                    _notify_student_payment(invoice.student, payment, receipt)

    return JsonResponse({'status': 'ok'}, status=200)


# ─────────────────────────────────────────────────────────────────────────────
# Receipts
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def receipt_detail_view(request, pk):
    """View a payment receipt."""
    receipt = get_object_or_404(
        Receipt.objects.select_related(
            'payment__invoice__student__user',
            'payment__invoice__session',
            'payment__invoice__term',
            'payment__recorded_by',
        ),
        pk=pk,
    )
    user = request.user
    # Access control
    if user.role == 'STUDENT':
        if not hasattr(user, 'student_profile') or user.student_profile != receipt.payment.invoice.student:
            messages.error(request, 'Access denied.')
            return redirect('finance:invoice_list')
    elif user.role == 'PARENT':
        try:
            if receipt.payment.invoice.student not in user.parent_profile.students.all():
                messages.error(request, 'Access denied.')
                return redirect('finance:invoice_list')
        except Exception:
            messages.error(request, 'Access denied.')
            return redirect('finance:invoice_list')

    return render(request, 'finance/receipt_detail.html', {
        'title': f'Receipt — {receipt.receipt_number}',
        'receipt': receipt,
        'school_name': settings.SCHOOL_NAME,
        'school_address': settings.SCHOOL_ADDRESS,
        'school_phone': settings.SCHOOL_PHONE,
    })


@login_required
def receipt_pdf_view(request, pk):
    """Download a receipt as PDF."""
    receipt = get_object_or_404(
        Receipt.objects.select_related(
            'payment__invoice__student__user',
            'payment__invoice__session',
            'payment__invoice__term',
        ),
        pk=pk,
    )
    user = request.user
    # Access control
    if user.role == 'STUDENT':
        if not hasattr(user, 'student_profile') or user.student_profile != receipt.payment.invoice.student:
            messages.error(request, 'Access denied.')
            return redirect('finance:invoice_list')

    return generate_pdf_response(
        template_name='finance/receipt_pdf.html',
        context={
            'receipt': receipt,
            'school_name': settings.SCHOOL_NAME,
            'school_address': settings.SCHOOL_ADDRESS,
            'school_phone': settings.SCHOOL_PHONE,
            'school_email': settings.SCHOOL_EMAIL,
        },
        filename=f'Receipt-{receipt.receipt_number}.pdf',
    )


# ─────────────────────────────────────────────────────────────────────────────
# Payment History
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def payment_history_view(request, student_pk=None):
    """
    Payment history.
    - Students/parents see their own history automatically.
    - Staff can pass student_pk to see a specific student.
    """
    user = request.user
    if user.role == 'STUDENT':
        try:
            student = user.student_profile
        except Student.DoesNotExist:
            messages.error(request, 'Student profile not found.')
            return redirect('dashboard:index')
    elif user.role == 'PARENT':
        try:
            students = user.parent_profile.students.all()
            payments = Payment.objects.filter(
                invoice__student__in=students, status='SUCCESS'
            ).select_related('invoice__student__user', 'invoice__session', 'invoice__term').order_by('-payment_date')
            return render(request, 'finance/payment_history.html', {
                'title': 'Payment History',
                'payments': paginate_queryset(payments, request, per_page=20),
            })
        except Exception:
            messages.error(request, 'Parent profile not found.')
            return redirect('dashboard:index')
    elif student_pk:
        student = get_object_or_404(Student, pk=student_pk)
    else:
        # Staff: show all payments
        qs = Payment.objects.filter(status='SUCCESS').select_related(
            'invoice__student__user', 'invoice__session', 'invoice__term'
        ).order_by('-payment_date')
        return render(request, 'finance/payment_history.html', {
            'title': 'All Payment History',
            'payments': paginate_queryset(qs, request, per_page=25),
        })

    payments = Payment.objects.filter(
        invoice__student=student, status='SUCCESS'
    ).select_related('invoice__session', 'invoice__term').order_by('-payment_date')

    return render(request, 'finance/payment_history.html', {
        'title': f'Payment History — {student.full_name}',
        'student': student,
        'payments': paginate_queryset(payments, request, per_page=20),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Reports
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT')
def outstanding_fees_report_view(request):
    """List all unpaid / partially paid invoices with optional filters."""
    form = FinanceReportFilterForm(request.GET or None)
    qs = Invoice.objects.filter(
        status__in=['UNPAID', 'PARTIAL']
    ).select_related('student__user', 'session', 'term')

    if form.is_valid():
        if form.cleaned_data.get('session'):
            qs = qs.filter(session=form.cleaned_data['session'])
        if form.cleaned_data.get('term'):
            qs = qs.filter(term=form.cleaned_data['term'])
        if form.cleaned_data.get('class_level'):
            qs = qs.filter(student__class_enrolled__class_level=form.cleaned_data['class_level'])
        if form.cleaned_data.get('date_from'):
            qs = qs.filter(created_at__date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data.get('date_to'):
            qs = qs.filter(created_at__date__lte=form.cleaned_data['date_to'])

    total_outstanding = qs.aggregate(
        total=Sum('total_amount'), paid=Sum('amount_paid')
    )
    outstanding_amount = (total_outstanding['total'] or 0) - (total_outstanding['paid'] or 0)

    return render(request, 'finance/outstanding_fees_report.html', {
        'title': 'Outstanding Fees Report',
        'form': form,
        'invoices': paginate_queryset(qs, request, per_page=30),
        'outstanding_amount': outstanding_amount,
        'total_invoices': qs.count(),
    })


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT')
def revenue_report_view(request):
    """
    Daily / monthly revenue report.
    Shows aggregated successful payments with optional date/session/term filter.
    """
    form = FinanceReportFilterForm(request.GET or None)
    qs = Payment.objects.filter(status='SUCCESS').select_related(
        'invoice__session', 'invoice__term', 'invoice__student__user'
    )

    if form.is_valid():
        if form.cleaned_data.get('date_from'):
            qs = qs.filter(payment_date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data.get('date_to'):
            qs = qs.filter(payment_date__lte=form.cleaned_data['date_to'])
        if form.cleaned_data.get('session'):
            qs = qs.filter(invoice__session=form.cleaned_data['session'])
        if form.cleaned_data.get('term'):
            qs = qs.filter(invoice__term=form.cleaned_data['term'])
        if form.cleaned_data.get('class_level'):
            qs = qs.filter(invoice__student__class_enrolled__class_level=form.cleaned_data['class_level'])

    total_revenue = qs.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

    # Daily aggregation for chart data
    from django.db.models.functions import TruncDate
    daily = (
        qs.annotate(day=TruncDate('payment_date'))
        .values('day')
        .annotate(total=Sum('amount_paid'))
        .order_by('day')
    )

    return render(request, 'finance/revenue_report.html', {
        'title': 'Revenue Report',
        'form': form,
        'payments': paginate_queryset(qs, request, per_page=30),
        'total_revenue': total_revenue,
        'daily_data': list(daily),
    })


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT')
def financial_summary_view(request):
    """Financial summary grouped by session and term."""
    sessions = AcademicSession.objects.prefetch_related('terms').all()
    summary = []
    for session in sessions:
        for term in session.terms.all():
            invoices = Invoice.objects.filter(session=session, term=term)
            agg = invoices.aggregate(
                total_invoiced=Sum('total_amount'),
                total_collected=Sum('amount_paid'),
            )
            total_invoiced = agg['total_invoiced'] or Decimal('0.00')
            total_collected = agg['total_collected'] or Decimal('0.00')
            summary.append({
                'session': session,
                'term': term,
                'total_invoiced': total_invoiced,
                'total_collected': total_collected,
                'outstanding': total_invoiced - total_collected,
                'invoice_count': invoices.count(),
                'paid_count': invoices.filter(status='PAID').count(),
            })

    return render(request, 'finance/financial_summary.html', {
        'title': 'Financial Summary',
        'summary': summary,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Export — Excel
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT')
def export_report_excel_view(request):
    """
    Export current revenue report to Excel.
    Accepts the same GET params as revenue_report_view.
    """
    form = FinanceReportFilterForm(request.GET or None)
    qs = Payment.objects.filter(status='SUCCESS').select_related(
        'invoice__session', 'invoice__term', 'invoice__student__user'
    ).order_by('-payment_date')

    if form.is_valid():
        if form.cleaned_data.get('date_from'):
            qs = qs.filter(payment_date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data.get('date_to'):
            qs = qs.filter(payment_date__lte=form.cleaned_data['date_to'])
        if form.cleaned_data.get('session'):
            qs = qs.filter(invoice__session=form.cleaned_data['session'])
        if form.cleaned_data.get('term'):
            qs = qs.filter(invoice__term=form.cleaned_data['term'])
        if form.cleaned_data.get('class_level'):
            qs = qs.filter(invoice__student__class_enrolled__class_level=form.cleaned_data['class_level'])

    wb, ws = create_excel_workbook('Revenue Report')
    columns = ['#', 'Date', 'Student', 'Invoice No.', 'Session', 'Term', 'Method', 'Amount (₦)', 'Reference']
    style_header_row(ws, 1, columns)

    for idx, payment in enumerate(qs, start=1):
        values = [
            idx,
            str(payment.payment_date),
            payment.invoice.student.full_name,
            payment.invoice.invoice_number,
            str(payment.invoice.session),
            str(payment.invoice.term),
            payment.get_payment_method_display(),
            float(payment.amount_paid),
            str(payment.payment_reference),
        ]
        style_data_row(ws, idx + 1, values, is_even=(idx % 2 == 0))

    auto_fit_columns(ws)
    return excel_response(wb, filename=f'revenue-report-{date.today()}.xlsx')


# ─────────────────────────────────────────────────────────────────────────────
# Export — PDF
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ACCOUNTANT')
def export_report_pdf_view(request):
    """Export revenue/outstanding report as PDF."""
    form = FinanceReportFilterForm(request.GET or None)
    qs = Payment.objects.filter(status='SUCCESS').select_related(
        'invoice__session', 'invoice__term', 'invoice__student__user'
    ).order_by('-payment_date')

    if form.is_valid():
        if form.cleaned_data.get('date_from'):
            qs = qs.filter(payment_date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data.get('date_to'):
            qs = qs.filter(payment_date__lte=form.cleaned_data['date_to'])
        if form.cleaned_data.get('session'):
            qs = qs.filter(invoice__session=form.cleaned_data['session'])
        if form.cleaned_data.get('term'):
            qs = qs.filter(invoice__term=form.cleaned_data['term'])

    total_revenue = qs.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

    return generate_pdf_response(
        template_name='finance/revenue_report_pdf.html',
        context={
            'payments': qs,
            'total_revenue': total_revenue,
            'school_name': settings.SCHOOL_NAME,
            'generated_on': timezone.now(),
            'filter_params': request.GET.urlencode(),
        },
        filename=f'revenue-report-{date.today()}.pdf',
    )
