"""
admissions/views.py

All views for the admissions workflow.
"""

import logging
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings

from accounts.models import User, Role
from academics.models import AcademicSession, ClassLevel
from core.utils import generate_pdf_response
from students.models import Student

from .forms import AdmissionForm, ApplicantForm, ApplicantReviewForm
from .models import Admission, Applicant, ApplicantStatus

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _is_admission_officer(user):
    """Return True for roles that can manage admissions."""
    return user.is_authenticated and user.role in [
        Role.SUPER_ADMIN, Role.ICT_ADMIN, Role.PRINCIPAL,
        Role.VICE_PRINCIPAL, Role.ADMISSION_OFFICER,
    ]


def _generate_application_number():
    """Generate a unique application number in APP{YYYY}-{NNNN} format."""
    year = date.today().year
    prefix = f"APP{year}-"
    last = (
        Applicant.objects
        .filter(application_number__startswith=prefix)
        .order_by('-application_number')
        .values_list('application_number', flat=True)
        .first()
    )
    if last:
        try:
            seq = int(last.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def _generate_admission_number():
    """Generate a unique admission number in STU{YYYY}{NNNN} format."""
    year = date.today().year
    prefix = f"STU{year}"
    last = (
        Student.objects
        .filter(admission_number__startswith=prefix)
        .order_by('-admission_number')
        .values_list('admission_number', flat=True)
        .first()
    )
    if last:
        try:
            seq = int(last[len(prefix):]) + 1
        except (ValueError, TypeError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def _send_application_confirmation(applicant, request):
    """Send confirmation email to applicant's guardian."""
    if not applicant.guardian_email:
        return
    school_name = getattr(settings, 'SCHOOL_NAME', 'SchoolOS Academy')
    subject = f"Application Received — {applicant.application_number}"
    body = render_to_string(
        'admissions/emails/application_confirmation.txt',
        {'applicant': applicant, 'school_name': school_name, 'request': request},
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[applicant.guardian_email],
            fail_silently=True,
        )
    except Exception as exc:
        logger.error("Failed to send application confirmation email: %s", exc)


def _send_admission_email(applicant, student, admission, request):
    """Send admission notification email to guardian."""
    if not applicant.guardian_email:
        return
    school_name = getattr(settings, 'SCHOOL_NAME', 'SchoolOS Academy')
    subject = f"Admission Confirmed — {student.admission_number}"
    body = render_to_string(
        'admissions/emails/admission_notification.txt',
        {
            'applicant': applicant,
            'student': student,
            'admission': admission,
            'school_name': school_name,
            'request': request,
        },
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[applicant.guardian_email],
            fail_silently=True,
        )
    except Exception as exc:
        logger.error("Failed to send admission email: %s", exc)


# ─── Public Views ─────────────────────────────────────────────────────────────

def application_form_view(request):
    """
    PUBLIC view — no login required.
    Renders the application form, generates an application number,
    saves the Applicant and sends a confirmation email.
    """
    if request.method == 'POST':
        form = ApplicantForm(request.POST, request.FILES)
        if form.is_valid():
            applicant = form.save(commit=False)
            applicant.application_number = _generate_application_number()
            applicant.status = ApplicantStatus.PENDING
            applicant.save()
            _send_application_confirmation(applicant, request)
            request.session['last_application_number'] = applicant.application_number
            return redirect('admissions:application_success')
    else:
        form = ApplicantForm()

    sessions = AcademicSession.objects.order_by('-start_date')
    class_levels = ClassLevel.objects.all()
    return render(request, 'admissions/application_form.html', {
        'form': form,
        'sessions': sessions,
        'class_levels': class_levels,
        'page_title': 'Apply for Admission',
    })


def application_success_view(request):
    """
    Show the application number after successful submission.
    Reads from session to avoid leaking data on direct URL access.
    """
    application_number = request.session.pop('last_application_number', None)
    school_name = getattr(settings, 'SCHOOL_NAME', 'SchoolOS Academy')
    return render(request, 'admissions/application_success.html', {
        'application_number': application_number,
        'school_name': school_name,
        'page_title': 'Application Submitted',
    })


# ─── Officer Views (login required) ──────────────────────────────────────────

officer_required = user_passes_test(
    _is_admission_officer,
    login_url=settings.LOGIN_URL,
)


@login_required
@officer_required
def applicant_list_view(request):
    """
    Paginated list of applicants with status filter and search.
    Accessible to admission officers and above.
    """
    qs = Applicant.objects.select_related('applying_for_class', 'session', 'reviewed_by')

    # Status filter
    status_filter = request.GET.get('status', '').strip()
    if status_filter and status_filter in ApplicantStatus.values:
        qs = qs.filter(status=status_filter)

    # Session filter
    session_filter = request.GET.get('session', '').strip()
    if session_filter:
        qs = qs.filter(session_id=session_filter)

    # Search
    search_query = request.GET.get('q', '').strip()
    if search_query:
        qs = qs.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(application_number__icontains=search_query) |
            Q(guardian_phone__icontains=search_query) |
            Q(guardian_email__icontains=search_query)
        )

    qs = qs.order_by('-created_at')
    paginator = Paginator(qs, 25)
    page = request.GET.get('page', 1)
    try:
        applicants = paginator.page(page)
    except PageNotAnInteger:
        applicants = paginator.page(1)
    except EmptyPage:
        applicants = paginator.page(paginator.num_pages)

    return render(request, 'admissions/applicant_list.html', {
        'applicants': applicants,
        'status_choices': ApplicantStatus.choices,
        'status_filter': status_filter,
        'session_filter': session_filter,
        'search_query': search_query,
        'sessions': AcademicSession.objects.order_by('-start_date'),
        'total_count': qs.count(),
        'page_title': 'Applicants',
    })


@login_required
@officer_required
def applicant_detail_view(request, pk):
    """Full details of a single applicant."""
    applicant = get_object_or_404(
        Applicant.objects.select_related('applying_for_class', 'session', 'reviewed_by'),
        pk=pk,
    )
    admission = getattr(applicant, 'admission', None)
    return render(request, 'admissions/applicant_detail.html', {
        'applicant': applicant,
        'admission': admission,
        'page_title': f'Applicant — {applicant.application_number}',
    })


@login_required
@officer_required
def applicant_review_view(request, pk):
    """
    Admission officer sets status (SCREENED / ADMITTED / REJECTED)
    with optional review notes.
    """
    applicant = get_object_or_404(Applicant, pk=pk)
    if request.method == 'POST':
        form = ApplicantReviewForm(request.POST, instance=applicant)
        if form.is_valid():
            reviewed = form.save(commit=False)
            reviewed.reviewed_by = request.user
            reviewed.review_date = timezone.now()
            reviewed.save()
            messages.success(
                request,
                f"Application {applicant.application_number} updated to "
                f"'{applicant.get_status_display()}'.",
            )
            return redirect('admissions:applicant_detail', pk=pk)
    else:
        form = ApplicantReviewForm(instance=applicant)

    return render(request, 'admissions/applicant_review.html', {
        'form': form,
        'applicant': applicant,
        'page_title': f'Review — {applicant.application_number}',
    })


@login_required
@officer_required
@transaction.atomic
def admit_applicant_view(request, pk):
    """
    Confirms admission:
    1. Creates a User account for the applicant.
    2. Creates a Student record linked to that user.
    3. Creates an Admission record.
    4. Updates applicant status to ENROLLED.
    5. Sends an admission notification email.
    """
    applicant = get_object_or_404(Applicant, pk=pk)

    # Guard: must be ADMITTED before enrollment
    if applicant.status not in [ApplicantStatus.ADMITTED, ApplicantStatus.SCREENED]:
        messages.error(
            request,
            "Applicant must be in ADMITTED or SCREENED status before enrollment.",
        )
        return redirect('admissions:applicant_detail', pk=pk)

    # Guard: already enrolled
    if hasattr(applicant, 'admission'):
        messages.warning(request, "This applicant has already been enrolled.")
        return redirect('admissions:admission_list')

    if request.method == 'POST':
        admission_number = _generate_admission_number()
        # Build a unique username from admission number
        username = admission_number.lower()
        # Temporary password — student should change on first login
        temp_password = f"SchoolOS@{date.today().year}"

        # Create User
        user = User.objects.create_user(
            username=username,
            email=applicant.guardian_email or f"{username}@schoolos.local",
            password=temp_password,
            first_name=applicant.first_name,
            last_name=applicant.last_name,
            role=Role.STUDENT,
            gender=applicant.gender,
            date_of_birth=applicant.date_of_birth,
            phone=applicant.guardian_phone,
        )

        # Create Student profile
        from academics.models import ClassArm
        # Try to find a default class arm for the applying_for_class
        class_arm = ClassArm.objects.filter(
            class_level=applicant.applying_for_class
        ).first()

        student = Student.objects.create(
            user=user,
            admission_number=admission_number,
            class_enrolled=class_arm,
            date_admitted=date.today(),
            religion=applicant.religion,
            nationality=applicant.nationality,
            state_of_origin=applicant.state_of_origin,
            lga=applicant.lga,
            previous_school=applicant.previous_school,
        )

        # Create Admission record
        admission = Admission.objects.create(
            applicant=applicant,
            student=student,
            admitted_by=request.user,
        )

        # Update applicant status
        applicant.status = ApplicantStatus.ENROLLED
        applicant.save(update_fields=['status'])

        # Send notification email
        _send_admission_email(applicant, student, admission, request)

        messages.success(
            request,
            f"Applicant admitted successfully. Admission number: {admission_number}.",
        )
        return redirect('admissions:admission_list')

    # GET: confirmation page
    return render(request, 'admissions/admit_confirm.html', {
        'applicant': applicant,
        'page_title': f'Admit — {applicant.application_number}',
    })


@login_required
@officer_required
def admission_letter_pdf_view(request, pk):
    """
    Generate and return a PDF admission letter for a given Admission record.
    Uses WeasyPrint via core.utils.generate_pdf_response.
    """
    admission = get_object_or_404(
        Admission.objects.select_related('applicant', 'student', 'student__user'),
        pk=pk,
    )
    school_name = getattr(settings, 'SCHOOL_NAME', 'SchoolOS Academy')
    school_address = getattr(settings, 'SCHOOL_ADDRESS', '')
    context = {
        'admission': admission,
        'applicant': admission.applicant,
        'student': admission.student,
        'school_name': school_name,
        'school_address': school_address,
        'issued_date': date.today(),
    }
    # Mark letter as generated
    if not admission.admission_letter_generated:
        admission.admission_letter_generated = True
        admission.save(update_fields=['admission_letter_generated'])

    filename = f"admission_letter_{admission.student.admission_number}.pdf"
    return generate_pdf_response('admissions/pdf/admission_letter.html', context, filename)


@login_required
@officer_required
def admission_list_view(request):
    """List all admission records with search."""
    qs = Admission.objects.select_related(
        'applicant', 'student', 'student__user', 'admitted_by'
    ).order_by('-admission_date')

    search_query = request.GET.get('q', '').strip()
    if search_query:
        qs = qs.filter(
            Q(applicant__first_name__icontains=search_query) |
            Q(applicant__last_name__icontains=search_query) |
            Q(student__admission_number__icontains=search_query) |
            Q(applicant__application_number__icontains=search_query)
        )

    paginator = Paginator(qs, 25)
    page = request.GET.get('page', 1)
    try:
        admissions = paginator.page(page)
    except PageNotAnInteger:
        admissions = paginator.page(1)
    except EmptyPage:
        admissions = paginator.page(paginator.num_pages)

    return render(request, 'admissions/admission_list.html', {
        'admissions': admissions,
        'search_query': search_query,
        'page_title': 'Admissions',
    })
