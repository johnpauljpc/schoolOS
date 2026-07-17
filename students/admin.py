"""
students/admin.py
-----------------
Django admin registrations for the students app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from students.models import (
    Enrollment,
    MedicalInfo,
    Parent,
    Student,
    StudentDocument,
)


# ─── Inlines ───────────────────────────────────────────────────────────────────

class MedicalInfoInline(admin.StackedInline):
    model = MedicalInfo
    can_delete = False
    verbose_name = 'Medical Information'
    verbose_name_plural = 'Medical Information'
    extra = 0
    fieldsets = (
        (_('Health'), {
            'fields': ('blood_group', 'genotype', 'allergies', 'medical_conditions', 'medications'),
        }),
        (_('Emergency Contact'), {
            'fields': ('emergency_contact_name', 'emergency_contact_phone'),
        }),
        (_('Doctor'), {
            'fields': ('doctor_name', 'doctor_phone'),
        }),
    )


class StudentDocumentInline(admin.TabularInline):
    model = StudentDocument
    extra = 0
    readonly_fields = ('uploaded_by', 'created_at')
    fields = ('doc_type', 'title', 'file', 'uploaded_by', 'created_at')


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    readonly_fields = ('date_enrolled',)
    fields = ('session', 'term', 'class_arm', 'is_active', 'date_enrolled')


# ─── Student Admin ─────────────────────────────────────────────────────────────

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'admission_number',
        'full_name',
        'class_enrolled',
        'status',
        'date_admitted',
        'nationality',
    )
    list_filter = ('status', 'class_enrolled__class_level', 'nationality')
    search_fields = (
        'admission_number',
        'user__first_name',
        'user__last_name',
        'user__email',
    )
    ordering = ('admission_number',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MedicalInfoInline, StudentDocumentInline, EnrollmentInline]
    fieldsets = (
        (_('User Account'), {
            'fields': ('user',),
        }),
        (_('Admission'), {
            'fields': ('admission_number', 'class_enrolled', 'date_admitted', 'status'),
        }),
        (_('Background'), {
            'fields': ('religion', 'nationality', 'state_of_origin', 'lga', 'previous_school'),
        }),
        (_('Notes'), {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def full_name(self, obj):
        return obj.user.full_name
    full_name.short_description = 'Name'
    full_name.admin_order_field = 'user__last_name'


# ─── Parent Admin ──────────────────────────────────────────────────────────────

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'relationship', 'occupation', 'phone')
    search_fields = (
        'user__first_name',
        'user__last_name',
        'user__email',
        'user__phone',
    )
    list_filter = ('relationship',)
    filter_horizontal = ('students',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (_('User Account'), {
            'fields': ('user',),
        }),
        (_('Guardian Details'), {
            'fields': ('relationship', 'occupation', 'office_address'),
        }),
        (_('Linked Students'), {
            'fields': ('students',),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def full_name(self, obj):
        return obj.user.full_name
    full_name.short_description = 'Name'
    full_name.admin_order_field = 'user__last_name'

    def phone(self, obj):
        return obj.user.phone
    phone.short_description = 'Phone'


# ─── Enrollment Admin ──────────────────────────────────────────────────────────

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'session', 'term', 'class_arm', 'is_active', 'date_enrolled')
    list_filter = ('session', 'term', 'class_arm__class_level', 'is_active')
    search_fields = (
        'student__admission_number',
        'student__user__first_name',
        'student__user__last_name',
    )
    readonly_fields = ('date_enrolled',)
