"""
students/views.py
-----------------
All views for the students app of SchoolOS.

Views:
  student_list_view            — paginated list with search/filter
  student_detail_view          — full student profile
  student_create_view          — create User(STUDENT) + Student
  student_update_view          — update Student profile
  student_medical_update_view  — update MedicalInfo
  student_document_upload_view — upload StudentDocument
  student_promote_view         — bulk promote students to next class
  student_transfer_view        — mark student as TRANSFERRED
  student_withdraw_view        — mark student as WITHDRAWN
  parent_list_view             — paginated parent list
  parent_create_view           — create User(PARENT) + Parent
  parent_update_view           — update Parent profile
  parent_link_student_view     — link parent ↔ student(s)
"""

import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import Role
from core.models import AuditLog
from students.forms import (
    MedicalInfoForm,
    ParentForm,
    ParentLinkStudentForm,
    ParentUserCreateForm,
    StudentDocumentForm,
    StudentForm,
    StudentPromotionForm,
    StudentSearchForm,
    StudentUserCreateForm,
)
from students.models import (
    Enrollment,
    MedicalInfo,
    Parent,
    Student,
    StudentDocument,
    StudentStatus,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _log_audit(request, action, model_name, object_id, object_repr, changes=''):
    AuditLog.objects.create(
        user=request.user,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        object_repr=object_repr,
        changes=changes,
        ip_address=_get_client_ip(request),
    )


# ─── Student Views ─────────────────────────────────────────────────────────────

@login_required
def student_list_view(request):
    """
    Paginated list of all students.
    Supports search by name / admission number / class arm name,
    and filtering by status or class arm.
    """
    form = StudentSearchForm(request.GET or None)
    queryset = (
        Student.objects.select_related('user', 'class_enrolled__class_level')
        .order_by('admission_number')
    )

    if form.is_valid():
        q = form.cleaned_data.get('search_query', '').strip()
        if q:
            queryset = queryset.filter(
                Q(admission_number__icontains=q) |
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(class_enrolled__name__icontains=q) |
                Q(class_enrolled__class_level__name__icontains=q)
            )
        status_filter = form.cleaned_data.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        class_filter = form.cleaned_data.get('class_enrolled')
        if class_filter:
            queryset = queryset.filter(class_enrolled=class_filter)

    total_count = queryset.count()
    paginator = Paginator(queryset, 25)
    page = request.GET.get('page', 1)
    try:
        students = paginator.page(page)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)

    return render(request, 'students/student_list.html', {
        'students': students,
        'form': form,
        'total_count': total_count,
        'page_title': 'Students',
    })


@login_required
def student_detail_view(request, pk):
    """Full student profile page — enrollments, documents, medical info."""
    student = get_object_or_404(
        Student.objects.select_related('user', 'class_enrolled__class_level'),
        pk=pk,
    )
    enrollments = (
        student.enrollments.select_related('session', 'term', 'class_arm__class_level')
        .order_by('-session__start_date', '-term__start_date')
    )
    documents = student.documents.select_related('uploaded_by').order_by('-created_at')
    parents = student.parents.select_related('user').all()

    medical_info = None
    try:
        medical_info = student.medical_info
    except MedicalInfo.DoesNotExist:
        pass

    return render(request, 'students/student_detail.html', {
        'student': student,
        'enrollments': enrollments,
        'documents': documents,
        'parents': parents,
        'medical_info': medical_info,
        'page_title': f'Student — {student.full_name}',
    })


@login_required
def student_create_view(request):
    """
    Create a new User (role=STUDENT) and associated Student profile.
    Both records are saved atomically.
    """
    if request.method == 'POST':
        form = StudentUserCreateForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=cd['username'],
                        password=cd['password'],
                        first_name=cd['first_name'],
                        last_name=cd['last_name'],
                        email=cd.get('email', ''),
                        phone=cd.get('phone', ''),
                        gender=cd.get('gender', ''),
                        date_of_birth=cd.get('date_of_birth'),
                        address=cd.get('address', ''),
                        role=Role.STUDENT,
                    )
                    student = Student.objects.create(
                        user=user,
                        admission_number=cd['admission_number'],
                        class_enrolled=cd.get('class_enrolled'),
                        date_admitted=cd.get('date_admitted'),
                        status=cd.get('status', StudentStatus.ACTIVE),
                        religion=cd.get('religion', ''),
                        nationality=cd.get('nationality', 'Nigerian'),
                        state_of_origin=cd.get('state_of_origin', ''),
                        lga=cd.get('lga', ''),
                        previous_school=cd.get('previous_school', ''),
                        notes=cd.get('notes', ''),
                    )
                _log_audit(
                    request, 'CREATE', 'Student', student.pk,
                    str(student),
                    f'Created student user {user.username}',
                )
                messages.success(
                    request,
                    f'Student "{student.full_name}" ({student.admission_number}) created successfully.',
                )
                return redirect('students:student_detail', pk=student.pk)
            except Exception as exc:
                logger.error('Failed to create student: %s', exc)
                messages.error(request, f'An error occurred: {exc}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentUserCreateForm()

    return render(request, 'students/student_form.html', {
        'form': form,
        'page_title': 'Enrol New Student',
    })


@login_required
def student_update_view(request, pk):
    """Update an existing Student's profile fields."""
    student = get_object_or_404(Student, pk=pk)

    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            changed = form.changed_data
            form.save()
            _log_audit(
                request, 'UPDATE', 'Student', student.pk, str(student),
                ', '.join(changed),
            )
            messages.success(request, 'Student profile updated successfully.')
            return redirect('students:student_detail', pk=student.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentForm(instance=student)

    return render(request, 'students/student_update.html', {
        'form': form,
        'student': student,
        'page_title': f'Edit Student — {student.full_name}',
    })


@login_required
def student_medical_update_view(request, pk):
    """Create or update the MedicalInfo record for a student."""
    student = get_object_or_404(Student, pk=pk)
    medical_info, _ = MedicalInfo.objects.get_or_create(student=student)

    if request.method == 'POST':
        form = MedicalInfoForm(request.POST, instance=medical_info)
        if form.is_valid():
            form.save()
            _log_audit(
                request, 'UPDATE', 'MedicalInfo', medical_info.pk, str(student),
                'Medical info updated',
            )
            messages.success(request, 'Medical information updated successfully.')
            return redirect('students:student_detail', pk=student.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MedicalInfoForm(instance=medical_info)

    return render(request, 'students/student_medical_update.html', {
        'form': form,
        'student': student,
        'page_title': f'Medical Info — {student.full_name}',
    })


@login_required
def student_document_upload_view(request, pk):
    """Upload a new StudentDocument for a student."""
    student = get_object_or_404(Student, pk=pk)

    if request.method == 'POST':
        form = StudentDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.student = student
            doc.uploaded_by = request.user
            doc.save()
            _log_audit(
                request, 'CREATE', 'StudentDocument', doc.pk, str(doc),
                f'Uploaded {doc.get_doc_type_display()}: {doc.title}',
            )
            messages.success(request, f'Document "{doc.title}" uploaded successfully.')
            return redirect('students:student_detail', pk=student.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentDocumentForm()

    return render(request, 'students/student_document_upload.html', {
        'form': form,
        'student': student,
        'page_title': f'Upload Document — {student.full_name}',
    })


@login_required
def student_promote_view(request):
    """
    Bulk-promote a selection of students to a new ClassArm.
    Updates class_enrolled on each Student record.
    """
    if request.method == 'POST':
        form = StudentPromotionForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            to_class = cd['to_class']
            selected_students = cd.get('students') or []
            count = 0
            with transaction.atomic():
                for s in selected_students:
                    s.class_enrolled = to_class
                    s.save(update_fields=['class_enrolled'])
                    count += 1
            _log_audit(
                request, 'UPDATE', 'Student', '',
                f'{count} students promoted',
                f'Promoted {count} student(s) to {to_class}',
            )
            messages.success(
                request,
                f'{count} student(s) promoted to {to_class} successfully.',
            )
            return redirect('students:student_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentPromotionForm()

    return render(request, 'students/student_promote.html', {
        'form': form,
        'page_title': 'Promote Students',
    })


@login_required
@require_http_methods(['POST'])
def student_transfer_view(request, pk):
    """Set a student's status to TRANSFERRED."""
    student = get_object_or_404(Student, pk=pk)
    student.status = StudentStatus.TRANSFERRED
    student.save(update_fields=['status'])
    _log_audit(
        request, 'UPDATE', 'Student', student.pk, str(student),
        'Status changed to TRANSFERRED',
    )
    messages.success(
        request,
        f'Student "{student.full_name}" has been marked as transferred.',
    )
    return redirect('students:student_detail', pk=student.pk)


@login_required
@require_http_methods(['POST'])
def student_withdraw_view(request, pk):
    """Set a student's status to WITHDRAWN."""
    student = get_object_or_404(Student, pk=pk)
    student.status = StudentStatus.WITHDRAWN
    student.save(update_fields=['status'])
    _log_audit(
        request, 'UPDATE', 'Student', student.pk, str(student),
        'Status changed to WITHDRAWN',
    )
    messages.success(
        request,
        f'Student "{student.full_name}" has been marked as withdrawn.',
    )
    return redirect('students:student_detail', pk=student.pk)


# ─── Parent Views ──────────────────────────────────────────────────────────────

@login_required
def parent_list_view(request):
    """Paginated list of all parents/guardians with optional search."""
    query = request.GET.get('q', '').strip()
    queryset = Parent.objects.select_related('user').order_by('user__last_name', 'user__first_name')
    if query:
        queryset = queryset.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(user__phone__icontains=query) |
            Q(occupation__icontains=query)
        )
    total_count = queryset.count()
    paginator = Paginator(queryset, 25)
    page = request.GET.get('page', 1)
    try:
        parents = paginator.page(page)
    except PageNotAnInteger:
        parents = paginator.page(1)
    except EmptyPage:
        parents = paginator.page(paginator.num_pages)

    return render(request, 'students/parent_list.html', {
        'parents': parents,
        'query': query,
        'total_count': total_count,
        'page_title': 'Parents & Guardians',
    })


@login_required
def parent_create_view(request):
    """Create a User (role=PARENT) + Parent profile in one atomic transaction."""
    if request.method == 'POST':
        form = ParentUserCreateForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=cd['username'],
                        password=cd['password'],
                        first_name=cd['first_name'],
                        last_name=cd['last_name'],
                        email=cd.get('email', ''),
                        phone=cd.get('phone', ''),
                        gender=cd.get('gender', ''),
                        address=cd.get('address', ''),
                        role=Role.PARENT,
                    )
                    parent = Parent.objects.create(
                        user=user,
                        relationship=cd['relationship'],
                        occupation=cd.get('occupation', ''),
                        office_address=cd.get('office_address', ''),
                    )
                _log_audit(
                    request, 'CREATE', 'Parent', parent.pk,
                    str(parent), f'Created parent user {user.username}',
                )
                messages.success(
                    request,
                    f'Parent "{parent}" created successfully.',
                )
                return redirect('students:parent_list')
            except Exception as exc:
                logger.error('Failed to create parent: %s', exc)
                messages.error(request, f'An error occurred: {exc}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ParentUserCreateForm()

    return render(request, 'students/parent_create.html', {
        'form': form,
        'page_title': 'Add Parent / Guardian',
    })


@login_required
def parent_update_view(request, pk):
    """Update an existing Parent's profile fields."""
    parent = get_object_or_404(Parent.objects.select_related('user'), pk=pk)

    if request.method == 'POST':
        form = ParentForm(request.POST, instance=parent)
        if form.is_valid():
            changed = form.changed_data
            form.save()
            _log_audit(
                request, 'UPDATE', 'Parent', parent.pk, str(parent),
                ', '.join(changed),
            )
            messages.success(request, 'Parent profile updated successfully.')
            return redirect('students:parent_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ParentForm(instance=parent)

    return render(request, 'students/parent_update.html', {
        'form': form,
        'parent': parent,
        'page_title': f'Edit Parent — {parent.user.full_name}',
    })


@login_required
def parent_link_student_view(request, pk):
    """
    Link (or unlink) a parent to one or more students.
    The M2M is replaced entirely with the submitted selection.
    """
    parent = get_object_or_404(Parent.objects.select_related('user'), pk=pk)

    if request.method == 'POST':
        form = ParentLinkStudentForm(request.POST)
        if form.is_valid():
            parent.students.set(form.cleaned_data.get('students') or [])
            _log_audit(
                request, 'UPDATE', 'Parent', parent.pk, str(parent),
                'Updated linked students',
            )
            messages.success(request, 'Student links updated successfully.')
            return redirect('students:parent_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ParentLinkStudentForm(initial={'students': parent.students.all()})

    return render(request, 'students/parent_link_student.html', {
        'form': form,
        'parent': parent,
        'page_title': f'Link Students — {parent.user.full_name}',
    })
