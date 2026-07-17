from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from core.decorators import role_required
from core.utils import (
    generate_pdf_response, create_excel_workbook,
    style_header_row, style_data_row, auto_fit_columns, excel_response
)


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'VICE_PRINCIPAL')
def report_index(request):
    return render(request, 'reports/index.html')


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'VICE_PRINCIPAL', 'ADMISSION_OFFICER')
def student_report(request):
    from students.models import Student, StudentStatus
    from academics.models import ClassArm
    qs = Student.objects.select_related('user', 'class_enrolled__class_level').all()
    class_id = request.GET.get('class_arm')
    status = request.GET.get('status', '')
    if class_id:
        qs = qs.filter(class_enrolled_id=class_id)
    if status:
        qs = qs.filter(status=status)
    summary = {
        'total': qs.count(),
        'active': qs.filter(status=StudentStatus.ACTIVE).count(),
        'graduated': qs.filter(status=StudentStatus.GRADUATED).count(),
        'withdrawn': qs.filter(status=StudentStatus.WITHDRAWN).count(),
    }
    class_arms = ClassArm.objects.select_related('class_level').order_by('class_level__order', 'name')
    return render(request, 'reports/student_report.html', {
        'students': qs[:100], 'summary': summary, 'class_arms': class_arms,
        'statuses': StudentStatus.choices, 'selected_class': class_id, 'selected_status': status
    })


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL')
def staff_report(request):
    from staff.models import Staff
    from academics.models import Department
    qs = Staff.objects.select_related('user', 'department').all()
    dept_id = request.GET.get('department')
    if dept_id:
        qs = qs.filter(department_id=dept_id)
    summary = {
        'total': qs.count(),
        'active': qs.filter(is_active=True).count(),
        'inactive': qs.filter(is_active=False).count(),
    }
    departments = Department.objects.all()
    return render(request, 'reports/staff_report.html', {
        'staff': qs, 'summary': summary, 'departments': departments, 'selected_dept': dept_id
    })


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'VICE_PRINCIPAL')
def academic_performance_report(request):
    from examinations.models import Result
    from academics.models import AcademicSession, AcademicTerm, ClassArm
    session_id = request.GET.get('session')
    term_id = request.GET.get('term')
    class_id = request.GET.get('class_arm')
    results = Result.objects.filter(is_published=True)
    if session_id:
        results = results.filter(session_id=session_id)
    if term_id:
        results = results.filter(term_id=term_id)
    if class_id:
        results = results.filter(class_arm_id=class_id)
    sessions = AcademicSession.objects.all()
    terms = AcademicTerm.objects.all()
    class_arms = ClassArm.objects.select_related('class_level').all()
    return render(request, 'reports/academic_report.html', {
        'results': results.select_related('student__user', 'subject')[:200],
        'sessions': sessions, 'terms': terms, 'class_arms': class_arms,
        'selected_session': session_id, 'selected_term': term_id, 'selected_class': class_id
    })


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'ADMISSION_OFFICER')
def admissions_report(request):
    from admissions.models import Applicant, ApplicantStatus
    qs = Applicant.objects.select_related('applying_for_class', 'session').all()
    summary = {s: qs.filter(status=s).count() for s, _ in ApplicantStatus.choices}
    return render(request, 'reports/admissions_report.html', {'applicants': qs, 'summary': summary})


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'ACCOUNTANT', 'PRINCIPAL')
def finance_report(request):
    from finance.models import Invoice, Payment
    from django.utils import timezone
    today = timezone.now().date()
    month_start = today.replace(day=1)
    total_invoiced = Invoice.objects.aggregate(t=Sum('total_amount'))['t'] or 0
    total_paid = Payment.objects.filter(status='SUCCESS').aggregate(t=Sum('amount_paid'))['t'] or 0
    monthly = Payment.objects.filter(status='SUCCESS', payment_date__gte=month_start).aggregate(t=Sum('amount_paid'))['t'] or 0
    unpaid = Invoice.objects.filter(status='UNPAID').count()
    return render(request, 'reports/finance_report.html', {
        'total_invoiced': total_invoiced, 'total_paid': total_paid,
        'monthly': monthly, 'unpaid': unpaid,
        'recent_payments': Payment.objects.select_related('invoice__student__user').order_by('-payment_date')[:20]
    })


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'ACCOUNTANT', 'PRINCIPAL')
def export_students_excel(request):
    from students.models import Student
    wb, ws = create_excel_workbook('Students')
    columns = ['Admission No.', 'First Name', 'Last Name', 'Class', 'Status', 'Date Admitted', 'Email']
    style_header_row(ws, 1, columns)
    for i, s in enumerate(Student.objects.select_related('user', 'class_enrolled__class_level').all(), 2):
        style_data_row(ws, i, [
            s.admission_number, s.user.first_name, s.user.last_name,
            str(s.class_enrolled) if s.class_enrolled else '',
            s.get_status_display(),
            str(s.date_admitted) if s.date_admitted else '',
            s.user.email
        ], is_even=(i % 2 == 0))
    auto_fit_columns(ws)
    return excel_response(wb, 'students_report.xlsx')


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'ACCOUNTANT', 'PRINCIPAL')
def export_finance_excel(request):
    from finance.models import Payment
    wb, ws = create_excel_workbook('Payments')
    columns = ['Reference', 'Student', 'Invoice', 'Amount (₦)', 'Method', 'Date', 'Status']
    style_header_row(ws, 1, columns)
    for i, p in enumerate(Payment.objects.select_related('invoice__student__user').order_by('-payment_date'), 2):
        style_data_row(ws, i, [
            str(p.payment_reference),
            p.invoice.student.user.get_full_name(),
            p.invoice.invoice_number,
            float(p.amount_paid),
            p.get_payment_method_display(),
            str(p.payment_date),
            p.get_status_display(),
        ], is_even=(i % 2 == 0))
    auto_fit_columns(ws)
    return excel_response(wb, 'finance_report.xlsx')
