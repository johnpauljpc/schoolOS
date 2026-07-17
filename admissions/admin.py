"""
admissions/admin.py

Django admin registrations for Applicant and Admission models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import Applicant, Admission, ApplicantStatus


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = [
        'application_number', 'full_name_display', 'applying_for_class',
        'session', 'status_badge', 'guardian_phone', 'created_at',
    ]
    list_filter = ['status', 'session', 'applying_for_class', 'gender']
    search_fields = [
        'first_name', 'last_name', 'application_number',
        'guardian_phone', 'guardian_email',
    ]
    readonly_fields = [
        'application_number', 'created_at', 'updated_at',
        'reviewed_by', 'review_date',
    ]
    ordering = ['-created_at']
    list_per_page = 30
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Personal Information', {
            'fields': (
                ('first_name', 'middle_name', 'last_name'),
                ('date_of_birth', 'gender'),
                ('religion', 'nationality'),
                ('state_of_origin', 'lga'),
                'passport_photo',
            )
        }),
        ('Academic', {
            'fields': (
                ('applying_for_class', 'session'),
                ('previous_school', 'previous_class'),
            )
        }),
        ('Guardian Information', {
            'fields': (
                'guardian_name',
                ('guardian_relationship', 'guardian_phone'),
                'guardian_email',
                'guardian_address',
            )
        }),
        ('Application Status', {
            'fields': (
                'application_number',
                'status',
                'review_notes',
                ('reviewed_by', 'review_date'),
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def full_name_display(self, obj):
        return obj.full_name
    full_name_display.short_description = 'Full Name'

    def status_badge(self, obj):
        colour_map = {
            ApplicantStatus.PENDING: '#f59e0b',
            ApplicantStatus.SCREENED: '#3b82f6',
            ApplicantStatus.ADMITTED: '#10b981',
            ApplicantStatus.REJECTED: '#ef4444',
            ApplicantStatus.ENROLLED: '#6366f1',
        }
        colour = colour_map.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:12px;font-size:0.8em;font-weight:600;">{}</span>',
            colour,
            obj.get_status_display(),
        )
    status_badge.short_description = 'Status'
    status_badge.allow_tags = True

    actions = ['mark_screened', 'mark_admitted', 'mark_rejected']

    def mark_screened(self, request, queryset):
        updated = queryset.filter(status=ApplicantStatus.PENDING).update(
            status=ApplicantStatus.SCREENED
        )
        self.message_user(request, f"{updated} applicant(s) marked as Screened.")
    mark_screened.short_description = 'Mark selected as Screened'

    def mark_admitted(self, request, queryset):
        updated = queryset.filter(
            status__in=[ApplicantStatus.PENDING, ApplicantStatus.SCREENED]
        ).update(status=ApplicantStatus.ADMITTED)
        self.message_user(request, f"{updated} applicant(s) marked as Admitted.")
    mark_admitted.short_description = 'Mark selected as Admitted'

    def mark_rejected(self, request, queryset):
        updated = queryset.filter(
            status__in=[ApplicantStatus.PENDING, ApplicantStatus.SCREENED]
        ).update(status=ApplicantStatus.REJECTED)
        self.message_user(request, f"{updated} applicant(s) marked as Rejected.")
    mark_rejected.short_description = 'Mark selected as Rejected'


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = [
        'applicant', 'student_link', 'admitted_by',
        'admission_date', 'admission_letter_generated',
    ]
    list_filter = ['admission_date', 'admission_letter_generated']
    search_fields = [
        'applicant__first_name', 'applicant__last_name',
        'applicant__application_number',
        'student__admission_number',
    ]
    readonly_fields = ['admission_date', 'admitted_by']
    raw_id_fields = ['applicant', 'student']
    list_per_page = 30
    date_hierarchy = 'admission_date'

    def student_link(self, obj):
        if obj.student:
            url = reverse('admin:students_student_change', args=[obj.student.pk])
            return format_html('<a href="{}">{}</a>', url, obj.student)
        return '—'
    student_link.short_description = 'Student'
