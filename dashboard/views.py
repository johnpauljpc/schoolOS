from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.utils import timezone
from accounts.models import User, Role
from communication.models import Announcement


@login_required
def index(request):
    """Route to the appropriate role-based dashboard."""
    user = request.user
    role = user.role

    context = {
        'user': user,
        'role': role,
        'today': timezone.now().date(),
    }

    if role in [Role.SUPER_ADMIN, Role.ICT_ADMIN]:
        return _admin_dashboard(request, context)
    elif role == Role.PRINCIPAL:
        return _principal_dashboard(request, context)
    elif role == Role.VICE_PRINCIPAL:
        return _vice_principal_dashboard(request, context)
    elif role == Role.ADMISSION_OFFICER:
        return _admission_dashboard(request, context)
    elif role == Role.ACCOUNTANT:
        return _accountant_dashboard(request, context)
    elif role in [Role.TEACHER, Role.CLASS_TEACHER]:
        return _teacher_dashboard(request, context)
    elif role == Role.STUDENT:
        return _student_dashboard(request, context)
    elif role == Role.PARENT:
        return _parent_dashboard(request, context)
    else:
        return render(request, 'dashboard/generic.html', context)


def _get_announcements(user):
    """Get announcements visible to the user's role."""
    from django.utils import timezone as tz
    now = tz.now()
    qs = Announcement.objects.filter(is_published=True).filter(
        Q(expiry_date__isnull=True) | Q(expiry_date__gte=now)
    ).filter(
        Q(publish_date__isnull=True) | Q(publish_date__lte=now)
    )
    visible = []
    for ann in qs[:20]:
        if ann.is_visible_to(user):
            visible.append(ann)
    return visible[:5]


def _admin_dashboard(request, context):
    from students.models import Student, StudentStatus
    from staff.models import Staff
    from admissions.models import Applicant, ApplicantStatus
    from finance.models import Invoice, Payment

    today = context['today']
    month_start = today.replace(day=1)

    context.update({
        'total_students': Student.objects.filter(status=StudentStatus.ACTIVE).count(),
        'total_staff': Staff.objects.filter(is_active=True).count(),
        'total_users': User.objects.filter(is_active=True).count(),
        'pending_admissions': Applicant.objects.filter(status=ApplicantStatus.PENDING).count(),
        'monthly_revenue': Payment.objects.filter(
            status='SUCCESS', payment_date__gte=month_start
        ).aggregate(total=Sum('amount_paid'))['total'] or 0,
        'outstanding_fees': Invoice.objects.filter(
            status__in=['UNPAID', 'PARTIAL']
        ).aggregate(bal=Sum('total_amount') - Sum('amount_paid'))['bal'] or 0,
        'recent_activity': [],
        'announcements': _get_announcements(request.user),
        'new_students_this_month': Student.objects.filter(
            created_at__date__gte=month_start
        ).count(),
    })
    return render(request, 'dashboard/admin_dashboard.html', context)


def _principal_dashboard(request, context):
    from students.models import Student, StudentStatus
    from staff.models import Staff
    from examinations.models import Result
    from admissions.models import Applicant, ApplicantStatus

    context.update({
        'total_students': Student.objects.filter(status=StudentStatus.ACTIVE).count(),
        'total_staff': Staff.objects.filter(is_active=True).count(),
        'pending_admissions': Applicant.objects.filter(status=ApplicantStatus.PENDING).count(),
        'pending_results': Result.objects.filter(is_approved=False, is_published=False).count(),
        'announcements': _get_announcements(request.user),
    })
    return render(request, 'dashboard/principal_dashboard.html', context)


def _vice_principal_dashboard(request, context):
    from students.models import Student, StudentStatus
    from examinations.models import Result

    context.update({
        'total_students': Student.objects.filter(status=StudentStatus.ACTIVE).count(),
        'pending_results': Result.objects.filter(is_approved=False).count(),
        'announcements': _get_announcements(request.user),
    })
    return render(request, 'dashboard/vice_principal_dashboard.html', context)


def _admission_dashboard(request, context):
    from admissions.models import Applicant, ApplicantStatus, Admission

    context.update({
        'pending_count': Applicant.objects.filter(status=ApplicantStatus.PENDING).count(),
        'screened_count': Applicant.objects.filter(status=ApplicantStatus.SCREENED).count(),
        'admitted_count': Applicant.objects.filter(status=ApplicantStatus.ADMITTED).count(),
        'rejected_count': Applicant.objects.filter(status=ApplicantStatus.REJECTED).count(),
        'recent_applicants': Applicant.objects.order_by('-created_at')[:8],
        'announcements': _get_announcements(request.user),
    })
    return render(request, 'dashboard/admission_dashboard.html', context)


def _accountant_dashboard(request, context):
    from finance.models import Invoice, Payment
    from django.utils import timezone as tz

    today = context['today']
    month_start = today.replace(day=1)

    context.update({
        'today_revenue': Payment.objects.filter(
            status='SUCCESS', payment_date=today
        ).aggregate(total=Sum('amount_paid'))['total'] or 0,
        'monthly_revenue': Payment.objects.filter(
            status='SUCCESS', payment_date__gte=month_start
        ).aggregate(total=Sum('amount_paid'))['total'] or 0,
        'unpaid_invoices': Invoice.objects.filter(status='UNPAID').count(),
        'partial_invoices': Invoice.objects.filter(status='PARTIAL').count(),
        'recent_payments': Payment.objects.select_related('invoice__student__user').order_by('-created_at')[:8],
        'announcements': _get_announcements(request.user),
    })
    return render(request, 'dashboard/accountant_dashboard.html', context)


def _teacher_dashboard(request, context):
    from academics.models import SubjectAssignment, ClassTimetable, AcademicTerm
    from students.models import Student

    user = request.user
    current_term = AcademicTerm.objects.filter(is_current=True).first()
    current_session = current_term.session if current_term else None

    assignments = SubjectAssignment.objects.filter(
        teacher=user, term=current_term, session=current_session
    ).select_related('subject', 'class_arm') if current_term else []

    # Students in teacher's classes
    class_arms = [a.class_arm for a in assignments]
    student_count = Student.objects.filter(class_enrolled__in=class_arms).count() if class_arms else 0

    context.update({
        'subject_assignments': assignments,
        'student_count': student_count,
        'current_term': current_term,
        'announcements': _get_announcements(request.user),
    })
    return render(request, 'dashboard/teacher_dashboard.html', context)


def _student_dashboard(request, context):
    from students.models import Student
    from finance.models import Invoice
    from examinations.models import Result

    try:
        student = request.user.student_profile
    except Student.DoesNotExist:
        context['no_profile'] = True
        return render(request, 'dashboard/student_dashboard.html', context)

    recent_results = Result.objects.filter(
        student=student, is_published=True
    ).select_related('subject', 'session', 'term').order_by('-created_at')[:5]

    outstanding = Invoice.objects.filter(
        student=student, status__in=['UNPAID', 'PARTIAL']
    ).first()

    context.update({
        'student': student,
        'recent_results': recent_results,
        'outstanding_invoice': outstanding,
        'announcements': _get_announcements(request.user),
    })
    return render(request, 'dashboard/student_dashboard.html', context)


def _parent_dashboard(request, context):
    from students.models import Parent, Student
    from finance.models import Invoice

    try:
        parent = request.user.parent_profile
        students = parent.students.select_related('user', 'class_enrolled').all()
    except Exception:
        students = []

    context.update({
        'children': students,
        'announcements': _get_announcements(request.user),
    })
    return render(request, 'dashboard/parent_dashboard.html', context)
