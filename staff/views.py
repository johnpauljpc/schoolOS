from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth import get_user_model
from core.decorators import role_required
from core.utils import paginate_queryset
from .models import Staff, StaffQualification, Teacher
from .forms import StaffForm, StaffSearchForm, StaffQualificationForm, TeacherForm

User = get_user_model()


@login_required
def staff_list(request):
    form = StaffSearchForm(request.GET)
    qs = Staff.objects.select_related('user', 'department').filter(is_active=True)
    q = request.GET.get('q', '').strip()
    dept = request.GET.get('department', '')
    if q:
        qs = qs.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(staff_id__icontains=q) |
            Q(designation__icontains=q)
        )
    if dept:
        qs = qs.filter(department_id=dept)
    staff = paginate_queryset(qs, request, per_page=20)
    return render(request, 'staff/staff_list.html', {'staff': staff, 'form': form, 'q': q})


@login_required
def staff_detail(request, pk):
    staff = get_object_or_404(Staff.objects.select_related('user', 'department'), pk=pk)
    qualifications = staff.qualifications.all()
    teacher_profile = getattr(staff, 'teacher_profile', None)
    return render(request, 'staff/staff_detail.html', {
        'staff': staff, 'qualifications': qualifications, 'teacher_profile': teacher_profile
    })


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL')
def staff_create(request):
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES)
        if form.is_valid():
            staff = form.save()
            messages.success(request, f'Staff member {staff.user.get_full_name()} created successfully.')
            return redirect('staff:detail', pk=staff.pk)
    else:
        form = StaffForm()
    return render(request, 'staff/staff_form.html', {'form': form, 'title': 'Add Staff Member'})


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL')
def staff_update(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff profile updated.')
            return redirect('staff:detail', pk=staff.pk)
    else:
        form = StaffForm(instance=staff)
    return render(request, 'staff/staff_form.html', {'form': form, 'staff': staff, 'title': 'Edit Staff'})


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL')
def staff_toggle_active(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    staff.is_active = not staff.is_active
    staff.save(update_fields=['is_active'])
    state = 'activated' if staff.is_active else 'deactivated'
    messages.success(request, f'Staff member {state}.')
    return redirect('staff:detail', pk=staff.pk)


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL')
def qualification_add(request, staff_pk):
    staff = get_object_or_404(Staff, pk=staff_pk)
    if request.method == 'POST':
        form = StaffQualificationForm(request.POST, request.FILES)
        if form.is_valid():
            qual = form.save(commit=False)
            qual.staff = staff
            qual.save()
            messages.success(request, 'Qualification added.')
            return redirect('staff:detail', pk=staff_pk)
    else:
        form = StaffQualificationForm()
    return render(request, 'staff/qualification_form.html', {'form': form, 'staff': staff})


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL')
def qualification_delete(request, pk):
    qual = get_object_or_404(StaffQualification, pk=pk)
    staff_pk = qual.staff.pk
    qual.delete()
    messages.success(request, 'Qualification removed.')
    return redirect('staff:detail', pk=staff_pk)


@login_required
def teacher_list(request):
    teachers = Teacher.objects.select_related(
        'staff__user', 'staff__department', 'class_assigned'
    ).prefetch_related('subjects').all()
    return render(request, 'staff/teacher_list.html', {'teachers': teachers})
