"""
examinations/views.py

All views for the examinations workflow:
  - Grade configuration CRUD
  - CA entry (formset, per class+subject+session+term)
  - Exam score entry (formset)
  - Result computation, approval, publishing
  - Report card and transcript PDF
  - Examination timetable management
  - Class timetable management
"""

import logging
from collections import defaultdict
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.conf import settings

from academics.models import AcademicSession, AcademicTerm, ClassArm, Subject
from accounts.models import Role
from core.utils import generate_pdf_response
from students.models import Enrollment, Student

from .forms import (
    AssessmentBulkForm,
    ClassTimetableForm,
    ExamScoreBulkForm,
    ExamTimetableForm,
    GradeConfigForm,
    ResultFilterForm,
)
from .models import (
    Assessment,
    ClassTimetable,
    ExaminationScore,
    ExaminationTimetable,
    GradeConfig,
    Result,
)

logger = logging.getLogger(__name__)


# ─── Permission helpers ───────────────────────────────────────────────────────

def _is_staff(user):
    return user.is_authenticated and user.is_staff_member


def _is_principal_or_admin(user):
    return user.is_authenticated and user.role in [
        Role.SUPER_ADMIN, Role.ICT_ADMIN, Role.PRINCIPAL, Role.VICE_PRINCIPAL
    ]


def _is_teacher_or_above(user):
    return user.is_authenticated and user.role in [
        Role.SUPER_ADMIN, Role.ICT_ADMIN, Role.PRINCIPAL, Role.VICE_PRINCIPAL,
        Role.TEACHER, Role.CLASS_TEACHER,
    ]


staff_required = user_passes_test(_is_staff, login_url=settings.LOGIN_URL)
principal_required = user_passes_test(_is_principal_or_admin, login_url=settings.LOGIN_URL)
teacher_required = user_passes_test(_is_teacher_or_above, login_url=settings.LOGIN_URL)


# ─── Helper: context selector form ───────────────────────────────────────────

def _build_selector_context():
    """Return common queryset context for selection dropdowns."""
    return {
        'sessions': AcademicSession.objects.order_by('-start_date'),
        'terms': AcademicTerm.objects.select_related('session').order_by(
            '-session__start_date', 'name'
        ),
        'class_arms': ClassArm.objects.select_related('class_level').order_by(
            'class_level__order', 'name'
        ),
        'subjects': Subject.objects.order_by('name'),
    }


def _get_enrolled_students(class_arm_id, session_id, term_id):
    """Return students enrolled in a given class arm / session / term."""
    enrollments = Enrollment.objects.filter(
        class_arm_id=class_arm_id,
        session_id=session_id,
        term_id=term_id,
        is_active=True,
    ).select_related('student__user').order_by('student__user__last_name', 'student__user__first_name')
    return [e.student for e in enrollments]


# ─── Grade Configuration ──────────────────────────────────────────────────────

@login_required
@staff_required
def grade_config_list_view(request):
    """List all grade configurations ordered by min_score descending."""
    configs = GradeConfig.objects.order_by('-min_score')
    return render(request, 'examinations/grade_config_list.html', {
        'configs': configs,
        'page_title': 'Grade Configurations',
    })


@login_required
@principal_required
def grade_config_create_view(request):
    """Create a new grade configuration."""
    if request.method == 'POST':
        form = GradeConfigForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grade configuration created successfully.')
            return redirect('examinations:grade_config_list')
    else:
        form = GradeConfigForm()

    return render(request, 'examinations/grade_config_form.html', {
        'form': form,
        'action': 'Create',
        'page_title': 'Create Grade Configuration',
    })


@login_required
@principal_required
def grade_config_update_view(request, pk):
    """Update an existing grade configuration."""
    config = get_object_or_404(GradeConfig, pk=pk)
    if request.method == 'POST':
        form = GradeConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grade configuration updated.')
            return redirect('examinations:grade_config_list')
    else:
        form = GradeConfigForm(instance=config)

    return render(request, 'examinations/grade_config_form.html', {
        'form': form,
        'config': config,
        'action': 'Update',
        'page_title': 'Update Grade Configuration',
    })


@login_required
@principal_required
def grade_config_delete_view(request, pk):
    """Confirm and delete a grade configuration."""
    config = get_object_or_404(GradeConfig, pk=pk)
    if request.method == 'POST':
        config.delete()
        messages.success(request, f'Grade configuration "{config}" deleted.')
        return redirect('examinations:grade_config_list')

    return render(request, 'examinations/grade_config_confirm_delete.html', {
        'config': config,
        'page_title': 'Delete Grade Configuration',
    })


# ─── CA Entry ─────────────────────────────────────────────────────────────────

@login_required
@teacher_required
def ca_entry_view(request):
    """
    Teacher selects class, subject, term, session → sees a formset of all
    enrolled students for CA1 / CA2 / CA3 entry.

    GET with query params: ?class_arm=<id>&subject=<id>&session=<id>&term=<id>
    POST: saves / updates Assessment records.
    """
    ctx = _build_selector_context()

    class_arm_id = request.GET.get('class_arm') or request.POST.get('class_arm')
    subject_id = request.GET.get('subject') or request.POST.get('subject')
    session_id = request.GET.get('session') or request.POST.get('session')
    term_id = request.GET.get('term') or request.POST.get('term')

    selected = all([class_arm_id, subject_id, session_id, term_id])
    students = []
    formset = None
    class_arm = subject = session = term = None

    if selected:
        try:
            class_arm = ClassArm.objects.get(pk=class_arm_id)
            subject = Subject.objects.get(pk=subject_id)
            session = AcademicSession.objects.get(pk=session_id)
            term = AcademicTerm.objects.get(pk=term_id)
        except (ClassArm.DoesNotExist, Subject.DoesNotExist,
                AcademicSession.DoesNotExist, AcademicTerm.DoesNotExist):
            messages.error(request, 'Invalid selection. Please try again.')
            return redirect('examinations:ca_entry')

        students = _get_enrolled_students(class_arm_id, session_id, term_id)

        if not students:
            messages.warning(
                request,
                'No students are enrolled in this class for the selected session/term.'
            )

        # Build initial data from existing Assessment records
        initial_data = []
        for student in students:
            existing = Assessment.objects.filter(
                student=student, subject=subject,
                session=session, term=term,
            ).first()
            initial_data.append({
                'student_id': student.pk,
                'student_name': student.full_name,
                'ca1': existing.ca1 if existing else 0,
                'ca2': existing.ca2 if existing else 0,
                'ca3': existing.ca3 if existing else 0,
            })

        if request.method == 'POST':
            formset = AssessmentBulkForm(request.POST, initial=initial_data)
            if formset.is_valid():
                saved_count = 0
                with transaction.atomic():
                    for i, form_data in enumerate(formset.cleaned_data):
                        if not form_data:
                            continue
                        student_id = form_data.get('student_id')
                        if not student_id:
                            continue
                        try:
                            student_obj = Student.objects.get(pk=student_id)
                        except Student.DoesNotExist:
                            continue
                        Assessment.objects.update_or_create(
                            student=student_obj,
                            subject=subject,
                            session=session,
                            term=term,
                            defaults={
                                'class_arm': class_arm,
                                'ca1': form_data.get('ca1', 0),
                                'ca2': form_data.get('ca2', 0),
                                'ca3': form_data.get('ca3', 0),
                                'entered_by': request.user,
                            },
                        )
                        saved_count += 1

                messages.success(
                    request,
                    f'CA scores saved for {saved_count} student(s).'
                )
                return redirect(
                    f"{request.path}?class_arm={class_arm_id}"
                    f"&subject={subject_id}&session={session_id}&term={term_id}"
                )
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            formset = AssessmentBulkForm(initial=initial_data)

    ctx.update({
        'formset': formset,
        'students': students,
        'class_arm': class_arm,
        'subject': subject,
        'session': session,
        'term': term,
        'class_arm_id': class_arm_id,
        'subject_id': subject_id,
        'session_id': session_id,
        'term_id': term_id,
        'selected': selected,
        'page_title': 'CA Score Entry',
    })
    return render(request, 'examinations/ca_entry.html', ctx)


# ─── Exam Score Entry ─────────────────────────────────────────────────────────

@login_required
@teacher_required
def exam_score_entry_view(request):
    """
    Same UX pattern as ca_entry_view but for exam scores (out of 60).

    GET with query params: ?class_arm=<id>&subject=<id>&session=<id>&term=<id>
    POST: saves / updates ExaminationScore records.
    """
    ctx = _build_selector_context()

    class_arm_id = request.GET.get('class_arm') or request.POST.get('class_arm')
    subject_id = request.GET.get('subject') or request.POST.get('subject')
    session_id = request.GET.get('session') or request.POST.get('session')
    term_id = request.GET.get('term') or request.POST.get('term')

    selected = all([class_arm_id, subject_id, session_id, term_id])
    students = []
    formset = None
    class_arm = subject = session = term = None

    if selected:
        try:
            class_arm = ClassArm.objects.get(pk=class_arm_id)
            subject = Subject.objects.get(pk=subject_id)
            session = AcademicSession.objects.get(pk=session_id)
            term = AcademicTerm.objects.get(pk=term_id)
        except (ClassArm.DoesNotExist, Subject.DoesNotExist,
                AcademicSession.DoesNotExist, AcademicTerm.DoesNotExist):
            messages.error(request, 'Invalid selection. Please try again.')
            return redirect('examinations:exam_score_entry')

        students = _get_enrolled_students(class_arm_id, session_id, term_id)

        if not students:
            messages.warning(
                request,
                'No students are enrolled in this class for the selected session/term.'
            )

        initial_data = []
        for student in students:
            existing = ExaminationScore.objects.filter(
                student=student, subject=subject,
                session=session, term=term,
            ).first()
            initial_data.append({
                'student_id': student.pk,
                'student_name': student.full_name,
                'score': existing.score if existing else 0,
            })

        if request.method == 'POST':
            formset = ExamScoreBulkForm(request.POST, initial=initial_data)
            if formset.is_valid():
                saved_count = 0
                with transaction.atomic():
                    for form_data in formset.cleaned_data:
                        if not form_data:
                            continue
                        student_id = form_data.get('student_id')
                        if not student_id:
                            continue
                        try:
                            student_obj = Student.objects.get(pk=student_id)
                        except Student.DoesNotExist:
                            continue
                        ExaminationScore.objects.update_or_create(
                            student=student_obj,
                            subject=subject,
                            session=session,
                            term=term,
                            defaults={
                                'class_arm': class_arm,
                                'score': form_data.get('score', 0),
                                'entered_by': request.user,
                            },
                        )
                        saved_count += 1

                messages.success(
                    request,
                    f'Exam scores saved for {saved_count} student(s).'
                )
                return redirect(
                    f"{request.path}?class_arm={class_arm_id}"
                    f"&subject={subject_id}&session={session_id}&term={term_id}"
                )
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            formset = ExamScoreBulkForm(initial=initial_data)

    ctx.update({
        'formset': formset,
        'students': students,
        'class_arm': class_arm,
        'subject': subject,
        'session': session,
        'term': term,
        'class_arm_id': class_arm_id,
        'subject_id': subject_id,
        'session_id': session_id,
        'term_id': term_id,
        'selected': selected,
        'page_title': 'Exam Score Entry',
    })
    return render(request, 'examinations/exam_score_entry.html', ctx)


# ─── Compute Results ──────────────────────────────────────────────────────────

@login_required
@principal_required
@transaction.atomic
def compute_results_view(request):
    """
    Admin / Principal computes all results for a class / session / term.
    For every enrolled student × every subject, ensures a Result exists
    then calls Result.compute().
    """
    ctx = _build_selector_context()

    if request.method == 'POST':
        class_arm_id = request.POST.get('class_arm')
        session_id = request.POST.get('session')
        term_id = request.POST.get('term')

        try:
            class_arm = ClassArm.objects.get(pk=class_arm_id)
            session = AcademicSession.objects.get(pk=session_id)
            term = AcademicTerm.objects.get(pk=term_id)
        except (ClassArm.DoesNotExist, AcademicSession.DoesNotExist, AcademicTerm.DoesNotExist):
            messages.error(request, 'Invalid class / session / term selection.')
            return render(request, 'examinations/compute_results.html', ctx)

        students = _get_enrolled_students(class_arm_id, session_id, term_id)
        if not students:
            messages.warning(request, 'No enrolled students found for the selected criteria.')
            return render(request, 'examinations/compute_results.html', ctx)

        # Collect subjects with CA or exam scores for this class/session/term
        subjects_with_ca = set(
            Assessment.objects.filter(
                class_arm=class_arm, session=session, term=term
            ).values_list('subject_id', flat=True)
        )
        subjects_with_exam = set(
            ExaminationScore.objects.filter(
                class_arm=class_arm, session=session, term=term
            ).values_list('subject_id', flat=True)
        )
        all_subject_ids = subjects_with_ca | subjects_with_exam
        subjects = Subject.objects.filter(pk__in=all_subject_ids)

        computed = 0
        errors = 0
        for student in students:
            for subject in subjects:
                try:
                    result, _ = Result.objects.get_or_create(
                        student=student,
                        subject=subject,
                        session=session,
                        term=term,
                        defaults={'class_arm': class_arm},
                    )
                    result.compute()
                    computed += 1
                except Exception as exc:
                    logger.error(
                        "Error computing result for %s / %s: %s", student, subject, exc
                    )
                    errors += 1

        # Assign positions per subject within this class
        _assign_positions(class_arm, session, term, subjects)

        msg = f'Computed {computed} result(s) for {class_arm}.'
        if errors:
            msg += f' {errors} error(s) occurred.'
        messages.success(request, msg)
        return redirect('examinations:result_list')

    return render(request, 'examinations/compute_results.html', {
        **ctx,
        'page_title': 'Compute Results',
    })


def _assign_positions(class_arm, session, term, subjects):
    """
    Assign class position to each student for each subject, in descending
    total_score order.
    """
    for subject in subjects:
        results = list(
            Result.objects.filter(
                class_arm=class_arm, session=session,
                term=term, subject=subject,
            ).order_by('-total_score')
        )
        for pos, result in enumerate(results, start=1):
            result.position = pos
            result.save(update_fields=['position'])


# ─── Results List ─────────────────────────────────────────────────────────────

@login_required
@staff_required
def result_list_view(request):
    """
    Display a table of results filtered by class, session, and term.
    """
    filter_form = ResultFilterForm(request.GET or None)
    qs = Result.objects.select_related(
        'student', 'student__user', 'subject',
        'class_arm', 'session', 'term',
    )

    if filter_form.is_valid():
        session = filter_form.cleaned_data.get('session')
        term = filter_form.cleaned_data.get('term')
        class_arm = filter_form.cleaned_data.get('class_arm')
        if session:
            qs = qs.filter(session=session)
        if term:
            qs = qs.filter(term=term)
        if class_arm:
            qs = qs.filter(class_arm=class_arm)

    qs = qs.order_by('class_arm', 'student__user__last_name', 'subject__name')
    paginator = Paginator(qs, 50)
    page = request.GET.get('page', 1)
    try:
        results = paginator.page(page)
    except PageNotAnInteger:
        results = paginator.page(1)
    except EmptyPage:
        results = paginator.page(paginator.num_pages)

    return render(request, 'examinations/result_list.html', {
        'filter_form': filter_form,
        'results': results,
        'total_count': qs.count(),
        'page_title': 'Results',
    })


# ─── Result Approval ──────────────────────────────────────────────────────────

@login_required
@principal_required
def result_approve_view(request):
    """
    Principal approves selected results (by result IDs in POST body).
    Typically invoked from the result_list page with checkboxes.
    """
    if request.method == 'POST':
        result_ids = request.POST.getlist('result_ids')
        if not result_ids:
            messages.warning(request, 'No results were selected for approval.')
            return redirect('examinations:result_list')

        updated = Result.objects.filter(
            pk__in=result_ids, is_approved=False
        ).update(
            is_approved=True,
            approved_by=request.user,
            approval_date=timezone.now(),
        )
        messages.success(request, f'{updated} result(s) approved.')
        return redirect('examinations:result_list')

    # GET: redirect back
    return redirect('examinations:result_list')


# ─── Result Publishing ────────────────────────────────────────────────────────

@login_required
@principal_required
def result_publish_view(request):
    """
    Publish approved results for a selected class / session / term so that
    students and parents can see their report cards.
    """
    ctx = _build_selector_context()

    if request.method == 'POST':
        class_arm_id = request.POST.get('class_arm')
        session_id = request.POST.get('session')
        term_id = request.POST.get('term')

        updated = Result.objects.filter(
            class_arm_id=class_arm_id,
            session_id=session_id,
            term_id=term_id,
            is_approved=True,
            is_published=False,
        ).update(is_published=True)

        messages.success(request, f'{updated} approved result(s) published.')
        return redirect('examinations:result_list')

    return render(request, 'examinations/result_publish.html', {
        **ctx,
        'page_title': 'Publish Results',
    })


# ─── Student Report Card ──────────────────────────────────────────────────────

@login_required
def student_report_card_view(request, student_id=None):
    """
    Students / Parents see their published report card.
    Admins / Teachers can view any student's report card.
    """
    # Determine which student to show
    if student_id and _is_staff(request.user):
        student = get_object_or_404(Student, pk=student_id)
    elif request.user.role == Role.STUDENT:
        student = get_object_or_404(Student, user=request.user)
    elif request.user.role == Role.PARENT:
        # Parents can only see their linked students
        parent_students = request.user.parent_profile.students.all()
        if student_id:
            student = get_object_or_404(parent_students, pk=student_id)
        else:
            student = parent_students.first()
            if not student:
                messages.error(request, 'No student linked to your account.')
                return redirect('dashboard:index')
    else:
        return HttpResponseForbidden('Access denied.')

    # Filter
    session_id = request.GET.get('session')
    term_id = request.GET.get('term')

    results_qs = Result.objects.filter(
        student=student, is_published=True,
    ).select_related('subject', 'session', 'term', 'class_arm')

    current_session = AcademicSession.get_current()
    current_term = AcademicTerm.get_current()

    if session_id:
        results_qs = results_qs.filter(session_id=session_id)
    elif current_session:
        results_qs = results_qs.filter(session=current_session)

    if term_id:
        results_qs = results_qs.filter(term_id=term_id)
    elif current_term:
        results_qs = results_qs.filter(term=current_term)

    results = results_qs.order_by('subject__name')

    # Summaries
    total_score = sum(r.total_score for r in results)
    average = (total_score / len(results)) if results else 0
    overall_grade_config = GradeConfig.get_grade_for_score(int(average))
    overall_grade = overall_grade_config.grade if overall_grade_config else '—'

    return render(request, 'examinations/report_card.html', {
        'student': student,
        'results': results,
        'total_score': total_score,
        'average': round(average, 2),
        'overall_grade': overall_grade,
        'sessions': AcademicSession.objects.order_by('-start_date'),
        'terms': AcademicTerm.objects.order_by('-session__start_date', 'name'),
        'selected_session_id': session_id or (str(current_session.pk) if current_session else ''),
        'selected_term_id': term_id or (str(current_term.pk) if current_term else ''),
        'page_title': f'Report Card — {student.full_name}',
    })


# ─── Report Card PDF ──────────────────────────────────────────────────────────

@login_required
def report_card_pdf_view(request, student_id):
    """PDF download of a student's report card."""
    # Staff can see any student; students/parents see own only
    if _is_staff(request.user):
        student = get_object_or_404(Student, pk=student_id)
    elif request.user.role == Role.STUDENT:
        student = get_object_or_404(Student, user=request.user, pk=student_id)
    elif request.user.role == Role.PARENT:
        student = get_object_or_404(
            request.user.parent_profile.students.all(), pk=student_id
        )
    else:
        return HttpResponseForbidden()

    session_id = request.GET.get('session')
    term_id = request.GET.get('term')
    current_session = AcademicSession.get_current()
    current_term = AcademicTerm.get_current()

    results_qs = Result.objects.filter(
        student=student, is_published=True,
    ).select_related('subject', 'session', 'term', 'class_arm')

    if session_id:
        results_qs = results_qs.filter(session_id=session_id)
    elif current_session:
        results_qs = results_qs.filter(session=current_session)

    if term_id:
        results_qs = results_qs.filter(term_id=term_id)
    elif current_term:
        results_qs = results_qs.filter(term=current_term)

    results = list(results_qs.order_by('subject__name'))
    total_score = sum(r.total_score for r in results)
    average = (total_score / len(results)) if results else 0
    overall_grade_config = GradeConfig.get_grade_for_score(int(average))

    context = {
        'student': student,
        'results': results,
        'total_score': total_score,
        'average': round(average, 2),
        'overall_grade': overall_grade_config.grade if overall_grade_config else '—',
        'overall_remark': overall_grade_config.remark if overall_grade_config else '—',
        'school_name': getattr(settings, 'SCHOOL_NAME', 'SchoolOS Academy'),
        'school_address': getattr(settings, 'SCHOOL_ADDRESS', ''),
        'issued_date': date.today(),
    }
    filename = f"report_card_{student.admission_number}.pdf"
    return generate_pdf_response('examinations/pdf/report_card.html', context, filename)


# ─── Transcript PDF ───────────────────────────────────────────────────────────

@login_required
def transcript_pdf_view(request, student_id):
    """
    All-time transcript PDF for a student.
    Groups results by session then term.
    """
    if _is_staff(request.user):
        student = get_object_or_404(Student, pk=student_id)
    elif request.user.role == Role.STUDENT:
        student = get_object_or_404(Student, user=request.user, pk=student_id)
    elif request.user.role == Role.PARENT:
        student = get_object_or_404(
            request.user.parent_profile.students.all(), pk=student_id
        )
    else:
        return HttpResponseForbidden()

    all_results = (
        Result.objects
        .filter(student=student, is_published=True)
        .select_related('subject', 'session', 'term', 'class_arm')
        .order_by('session__start_date', 'term__name', 'subject__name')
    )

    # Group: {session: {term: [results]}}
    grouped = defaultdict(lambda: defaultdict(list))
    for result in all_results:
        grouped[result.session][result.term].append(result)

    # Convert to sorted list of tuples for template
    structured = [
        (session, sorted(terms.items(), key=lambda x: x[0].name))
        for session, terms in sorted(grouped.items(), key=lambda x: x[0].start_date)
    ]

    context = {
        'student': student,
        'structured': structured,
        'school_name': getattr(settings, 'SCHOOL_NAME', 'SchoolOS Academy'),
        'school_address': getattr(settings, 'SCHOOL_ADDRESS', ''),
        'issued_date': date.today(),
    }
    filename = f"transcript_{student.admission_number}.pdf"
    return generate_pdf_response('examinations/pdf/transcript.html', context, filename)


# ─── Examination Timetable ────────────────────────────────────────────────────

@login_required
@staff_required
def exam_timetable_list_view(request):
    """List examination timetable entries with optional filters."""
    qs = ExaminationTimetable.objects.select_related(
        'subject', 'class_arm', 'session', 'term'
    ).order_by('exam_date', 'start_time')

    session_id = request.GET.get('session')
    term_id = request.GET.get('term')
    class_arm_id = request.GET.get('class_arm')

    if session_id:
        qs = qs.filter(session_id=session_id)
    if term_id:
        qs = qs.filter(term_id=term_id)
    if class_arm_id:
        qs = qs.filter(class_arm_id=class_arm_id)

    ctx = _build_selector_context()
    ctx.update({
        'timetable_entries': qs,
        'session_filter': session_id,
        'term_filter': term_id,
        'class_arm_filter': class_arm_id,
        'page_title': 'Examination Timetable',
    })
    return render(request, 'examinations/exam_timetable_list.html', ctx)


@login_required
@principal_required
def exam_timetable_create_view(request):
    """Create a new examination timetable entry."""
    if request.method == 'POST':
        form = ExamTimetableForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Examination timetable entry created.')
            return redirect('examinations:exam_timetable_list')
    else:
        form = ExamTimetableForm()

    return render(request, 'examinations/exam_timetable_form.html', {
        'form': form,
        'action': 'Create',
        'page_title': 'Create Exam Timetable Entry',
    })


# ─── Class Timetable ──────────────────────────────────────────────────────────

@login_required
@staff_required
def class_timetable_view(request, class_arm_id=None):
    """
    Show the weekly timetable grid for a selected class arm.
    Columns = days (Mon–Fri), rows sorted by start time.
    """
    ctx = _build_selector_context()

    class_arm = None
    timetable_by_day = {}  # {day_number: [slots]}
    session_id = request.GET.get('session')
    term_id = request.GET.get('term')

    if class_arm_id:
        class_arm = get_object_or_404(ClassArm, pk=class_arm_id)
        qs = ClassTimetable.objects.filter(
            class_arm=class_arm,
        ).select_related('subject', 'teacher', 'session', 'term')

        if session_id:
            qs = qs.filter(session_id=session_id)
        if term_id:
            qs = qs.filter(term_id=term_id)

        qs = qs.order_by('day_of_week', 'start_time')
        for slot in qs:
            timetable_by_day.setdefault(slot.day_of_week, []).append(slot)

    # Build grid structure
    DAY_CHOICES = ClassTimetable.DAY_CHOICES  # [(0,'Monday'), ...]
    timetable_grid = [
        (day_num, day_name, timetable_by_day.get(day_num, []))
        for day_num, day_name in DAY_CHOICES
    ]

    ctx.update({
        'class_arm': class_arm,
        'timetable_grid': timetable_grid,
        'class_arm_id': class_arm_id,
        'session_filter': session_id,
        'term_filter': term_id,
        'page_title': f'Class Timetable — {class_arm}' if class_arm else 'Class Timetable',
    })
    return render(request, 'examinations/class_timetable.html', ctx)


@login_required
@principal_required
def class_timetable_create_view(request):
    """Create a new class timetable slot."""
    if request.method == 'POST':
        form = ClassTimetableForm(request.POST)
        if form.is_valid():
            entry = form.save()
            messages.success(request, 'Timetable slot created.')
            return redirect(
                'examinations:class_timetable',
                class_arm_id=entry.class_arm.pk,
            )
    else:
        # Pre-fill class_arm from GET param
        initial = {}
        if request.GET.get('class_arm'):
            initial['class_arm'] = request.GET.get('class_arm')
        form = ClassTimetableForm(initial=initial)

    return render(request, 'examinations/class_timetable_form.html', {
        'form': form,
        'action': 'Create',
        'page_title': 'Create Timetable Slot',
    })
