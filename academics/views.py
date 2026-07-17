"""
academics/views.py

CRUD views for all academics models.
Principle: read operations accessible to any logged-in staff member;
           write/delete operations restricted to SUPER_ADMIN, ICT_ADMIN, or PRINCIPAL.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import role_required, staff_required

from .forms import (
    AcademicSessionForm,
    AcademicTermForm,
    ClassArmForm,
    ClassLevelForm,
    ClassTeacherAssignmentForm,
    DepartmentForm,
    SubjectAssignmentForm,
    SubjectForm,
)
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

# Roles allowed to perform write operations
ADMIN_ROLES = ('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'VICE_PRINCIPAL')


# =============================================================================
# AcademicSession views
# =============================================================================

@login_required
@staff_required
def session_list(request):
    """List all academic sessions."""
    sessions = AcademicSession.objects.all().order_by('-start_date')
    paginator = Paginator(sessions, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'academics/session_list.html', {
        'page_obj': page_obj,
        'sessions': page_obj.object_list,
        'title':    'Academic Sessions',
    })


@login_required
@role_required(*ADMIN_ROLES)
def session_create(request):
    """Create a new academic session."""
    form = AcademicSessionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        session = form.save()
        messages.success(request, f'Session "{session.name}" created successfully.')
        return redirect('academics:session_list')
    return render(request, 'academics/session_form.html', {
        'form':  form,
        'title': 'Create Academic Session',
        'action': 'Create',
    })


@login_required
@role_required(*ADMIN_ROLES)
def session_update(request, pk):
    """Edit an existing academic session."""
    session = get_object_or_404(AcademicSession, pk=pk)
    form    = AcademicSessionForm(request.POST or None, instance=session)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Session "{session.name}" updated successfully.')
        return redirect('academics:session_list')
    return render(request, 'academics/session_form.html', {
        'form':    form,
        'title':   f'Edit Session — {session.name}',
        'action':  'Update',
        'object':  session,
    })


@login_required
@role_required(*ADMIN_ROLES)
def session_set_current(request, pk):
    """Mark a session as the current session."""
    session = get_object_or_404(AcademicSession, pk=pk)
    AcademicSession.objects.exclude(pk=pk).update(is_current=False)
    session.is_current = True
    session.save(update_fields=['is_current'])
    messages.success(request, f'"{session.name}" is now the current session.')
    return redirect('academics:session_list')


# =============================================================================
# AcademicTerm views
# =============================================================================

@login_required
@staff_required
def term_list(request):
    """List all academic terms."""
    terms = AcademicTerm.objects.select_related('session').order_by('-session__start_date', 'name')
    paginator = Paginator(terms, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'academics/term_list.html', {
        'page_obj': page_obj,
        'terms':    page_obj.object_list,
        'title':    'Academic Terms',
    })


@login_required
@role_required(*ADMIN_ROLES)
def term_create(request):
    """Create a new academic term."""
    form = AcademicTermForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            term = form.save()
            messages.success(request, f'Term "{term}" created successfully.')
            return redirect('academics:term_list')
        except IntegrityError:
            messages.error(request, 'That term already exists for the selected session.')
    return render(request, 'academics/term_form.html', {
        'form':  form,
        'title': 'Create Academic Term',
        'action': 'Create',
    })


@login_required
@role_required(*ADMIN_ROLES)
def term_update(request, pk):
    """Edit an existing academic term."""
    term = get_object_or_404(AcademicTerm, pk=pk)
    form = AcademicTermForm(request.POST or None, instance=term)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Term "{term}" updated successfully.')
        return redirect('academics:term_list')
    return render(request, 'academics/term_form.html', {
        'form':   form,
        'title':  f'Edit Term — {term}',
        'action': 'Update',
        'object': term,
    })


@login_required
@role_required(*ADMIN_ROLES)
def term_set_current(request, pk):
    """Mark a term as the current term."""
    term = get_object_or_404(AcademicTerm, pk=pk)
    AcademicTerm.objects.exclude(pk=pk).update(is_current=False)
    term.is_current = True
    term.save(update_fields=['is_current'])
    messages.success(request, f'"{term}" is now the current term.')
    return redirect('academics:term_list')


# =============================================================================
# Department views
# =============================================================================

@login_required
@staff_required
def department_list(request):
    """List all departments."""
    departments = Department.objects.select_related('head').all()
    return render(request, 'academics/department_list.html', {
        'departments': departments,
        'title':       'Departments',
    })


@login_required
@role_required(*ADMIN_ROLES)
def department_create(request):
    """Create a new department."""
    form = DepartmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        dept = form.save()
        messages.success(request, f'Department "{dept.name}" created successfully.')
        return redirect('academics:department_list')
    return render(request, 'academics/department_form.html', {
        'form':  form,
        'title': 'Create Department',
        'action': 'Create',
    })


@login_required
@role_required(*ADMIN_ROLES)
def department_update(request, pk):
    """Edit an existing department."""
    dept = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(request.POST or None, instance=dept)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Department "{dept.name}" updated successfully.')
        return redirect('academics:department_list')
    return render(request, 'academics/department_form.html', {
        'form':   form,
        'title':  f'Edit Department — {dept.name}',
        'action': 'Update',
        'object': dept,
    })


# =============================================================================
# ClassLevel views
# =============================================================================

@login_required
@staff_required
def class_level_list(request):
    """List all class levels."""
    levels = ClassLevel.objects.all()
    return render(request, 'academics/class_level_list.html', {
        'levels': levels,
        'title':  'Class Levels',
    })


@login_required
@role_required(*ADMIN_ROLES)
def class_level_create(request):
    """Create a new class level."""
    form = ClassLevelForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        level = form.save()
        messages.success(request, f'Class level "{level.name}" created successfully.')
        return redirect('academics:class_level_list')
    return render(request, 'academics/class_level_form.html', {
        'form':  form,
        'title': 'Create Class Level',
        'action': 'Create',
    })


@login_required
@role_required(*ADMIN_ROLES)
def class_level_update(request, pk):
    """Edit an existing class level."""
    level = get_object_or_404(ClassLevel, pk=pk)
    form  = ClassLevelForm(request.POST or None, instance=level)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Class level "{level.name}" updated.')
        return redirect('academics:class_level_list')
    return render(request, 'academics/class_level_form.html', {
        'form':   form,
        'title':  f'Edit Class Level — {level.name}',
        'action': 'Update',
        'object': level,
    })


# =============================================================================
# ClassArm views
# =============================================================================

@login_required
@staff_required
def class_arm_list(request):
    """List all class arms."""
    arms = ClassArm.objects.select_related('class_level').all()
    return render(request, 'academics/class_arm_list.html', {
        'arms':  arms,
        'title': 'Class Arms',
    })


@login_required
@role_required(*ADMIN_ROLES)
def class_arm_create(request):
    """Create a new class arm."""
    form = ClassArmForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            arm = form.save()
            messages.success(request, f'Class arm "{arm}" created successfully.')
            return redirect('academics:class_arm_list')
        except IntegrityError:
            messages.error(request, 'An arm with that name already exists for this class level.')
    return render(request, 'academics/class_arm_form.html', {
        'form':  form,
        'title': 'Create Class Arm',
        'action': 'Create',
    })


@login_required
@role_required(*ADMIN_ROLES)
def class_arm_update(request, pk):
    """Edit an existing class arm."""
    arm  = get_object_or_404(ClassArm, pk=pk)
    form = ClassArmForm(request.POST or None, instance=arm)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Class arm "{arm}" updated.')
        return redirect('academics:class_arm_list')
    return render(request, 'academics/class_arm_form.html', {
        'form':   form,
        'title':  f'Edit Class Arm — {arm}',
        'action': 'Update',
        'object': arm,
    })


# =============================================================================
# Subject views
# =============================================================================

@login_required
@staff_required
def subject_list(request):
    """List all subjects with optional search."""
    qs = Subject.objects.select_related('department').prefetch_related('class_levels')
    q  = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(name__icontains=q) | qs.filter(code__icontains=q)
    paginator = Paginator(qs.distinct().order_by('name'), 25)
    page_obj  = paginator.get_page(request.GET.get('page'))
    return render(request, 'academics/subject_list.html', {
        'page_obj': page_obj,
        'subjects': page_obj.object_list,
        'title':    'Subjects',
        'q':        q,
    })


@login_required
@role_required(*ADMIN_ROLES)
def subject_create(request):
    """Create a new subject."""
    form = SubjectForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        subject = form.save()
        messages.success(request, f'Subject "{subject.name}" created successfully.')
        return redirect('academics:subject_list')
    return render(request, 'academics/subject_form.html', {
        'form':  form,
        'title': 'Create Subject',
        'action': 'Create',
    })


@login_required
@role_required(*ADMIN_ROLES)
def subject_update(request, pk):
    """Edit an existing subject."""
    subject = get_object_or_404(Subject, pk=pk)
    form    = SubjectForm(request.POST or None, instance=subject)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Subject "{subject.name}" updated.')
        return redirect('academics:subject_list')
    return render(request, 'academics/subject_form.html', {
        'form':   form,
        'title':  f'Edit Subject — {subject.name}',
        'action': 'Update',
        'object': subject,
    })


@login_required
@role_required(*ADMIN_ROLES)
def subject_delete(request, pk):
    """Delete a subject (POST only)."""
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        name = subject.name
        subject.delete()
        messages.success(request, f'Subject "{name}" deleted successfully.')
        return redirect('academics:subject_list')
    return render(request, 'academics/confirm_delete.html', {
        'object':      subject,
        'object_name': subject.name,
        'cancel_url':  'academics:subject_list',
        'title':       f'Delete Subject — {subject.name}',
    })


# =============================================================================
# SubjectAssignment views
# =============================================================================

@login_required
@staff_required
def subject_assignment_list(request):
    """List all subject assignments with optional filters."""
    qs = SubjectAssignment.objects.select_related(
        'teacher', 'subject', 'class_arm', 'class_arm__class_level', 'session', 'term'
    )
    session_id = request.GET.get('session')
    term_id    = request.GET.get('term')
    arm_id     = request.GET.get('class_arm')

    if session_id:
        qs = qs.filter(session_id=session_id)
    if term_id:
        qs = qs.filter(term_id=term_id)
    if arm_id:
        qs = qs.filter(class_arm_id=arm_id)

    paginator = Paginator(qs.order_by('class_arm', 'subject'), 30)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'academics/subject_assignment_list.html', {
        'page_obj':    page_obj,
        'assignments': page_obj.object_list,
        'sessions':    AcademicSession.objects.all(),
        'terms':       AcademicTerm.objects.select_related('session').all(),
        'class_arms':  ClassArm.objects.select_related('class_level').all(),
        'title':       'Subject Assignments',
        'filter_session': session_id,
        'filter_term':    term_id,
        'filter_arm':     arm_id,
    })


@login_required
@role_required(*ADMIN_ROLES)
def subject_assignment_create(request):
    """Create a new subject assignment."""
    form = SubjectAssignmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            assignment = form.save()
            messages.success(request, f'Assignment created: {assignment}')
            return redirect('academics:subject_assignment_list')
        except IntegrityError:
            messages.error(request, 'This assignment already exists (duplicate).')
    return render(request, 'academics/subject_assignment_form.html', {
        'form':  form,
        'title': 'Assign Subject to Teacher',
        'action': 'Create',
    })


@login_required
@role_required(*ADMIN_ROLES)
def subject_assignment_delete(request, pk):
    """Delete a subject assignment."""
    assignment = get_object_or_404(SubjectAssignment, pk=pk)
    if request.method == 'POST':
        assignment.delete()
        messages.success(request, 'Subject assignment removed.')
        return redirect('academics:subject_assignment_list')
    return render(request, 'academics/confirm_delete.html', {
        'object':      assignment,
        'object_name': str(assignment),
        'cancel_url':  'academics:subject_assignment_list',
        'title':       'Remove Subject Assignment',
    })


# =============================================================================
# ClassTeacherAssignment views
# =============================================================================

@login_required
@staff_required
def class_teacher_assignment_list(request):
    """List all class teacher assignments."""
    qs = ClassTeacherAssignment.objects.select_related(
        'teacher', 'class_arm', 'class_arm__class_level', 'session'
    )
    session_id = request.GET.get('session')
    if session_id:
        qs = qs.filter(session_id=session_id)

    paginator = Paginator(qs.order_by('session', 'class_arm'), 30)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'academics/class_teacher_assignment_list.html', {
        'page_obj':    page_obj,
        'assignments': page_obj.object_list,
        'sessions':    AcademicSession.objects.all(),
        'title':       'Class Teacher Assignments',
        'filter_session': session_id,
    })


@login_required
@role_required(*ADMIN_ROLES)
def class_teacher_assignment_create(request):
    """Assign a class teacher to a class arm for a session."""
    form = ClassTeacherAssignmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            ct = form.save()
            messages.success(request, f'Class teacher assigned: {ct}')
            return redirect('academics:class_teacher_assignment_list')
        except IntegrityError:
            messages.error(
                request,
                'This class arm already has a class teacher for the selected session.'
            )
    return render(request, 'academics/class_teacher_assignment_form.html', {
        'form':  form,
        'title': 'Assign Class Teacher',
        'action': 'Create',
    })
