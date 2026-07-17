"""
academics/admin.py

Django admin registration for all academics models.
"""

from django.contrib import admin

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


# ---------------------------------------------------------------------------
# AcademicSession
# ---------------------------------------------------------------------------

@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display  = ('name', 'start_date', 'end_date', 'is_current', 'created_at')
    list_filter   = ('is_current',)
    search_fields = ('name',)
    ordering      = ('-start_date',)
    readonly_fields = ('created_at', 'updated_at')
    actions       = ['set_as_current']

    @admin.action(description='Set selected session as current')
    def set_as_current(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, 'Please select exactly one session.', level='warning')
            return
        session = queryset.first()
        AcademicSession.objects.exclude(pk=session.pk).update(is_current=False)
        session.is_current = True
        session.save(update_fields=['is_current'])
        self.message_user(request, f'"{session.name}" is now the current session.')


# ---------------------------------------------------------------------------
# AcademicTerm
# ---------------------------------------------------------------------------

class AcademicTermInline(admin.TabularInline):
    model  = AcademicTerm
    extra  = 0
    fields = ('name', 'start_date', 'end_date', 'is_current', 'next_term_begins')
    show_change_link = True


@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display  = ('__str__', 'session', 'start_date', 'end_date', 'is_current')
    list_filter   = ('is_current', 'session', 'name')
    search_fields = ('session__name',)
    ordering      = ('-session__start_date', 'name')
    readonly_fields = ('created_at', 'updated_at')
    actions       = ['set_as_current']

    @admin.action(description='Set selected term as current')
    def set_as_current(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, 'Please select exactly one term.', level='warning')
            return
        term = queryset.first()
        AcademicTerm.objects.exclude(pk=term.pk).update(is_current=False)
        term.is_current = True
        term.save(update_fields=['is_current'])
        self.message_user(request, f'"{term}" is now the current term.')


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display  = ('name', 'head', 'created_at')
    search_fields = ('name', 'head__first_name', 'head__last_name')
    autocomplete_fields = []
    readonly_fields = ('created_at', 'updated_at')


# ---------------------------------------------------------------------------
# ClassLevel
# ---------------------------------------------------------------------------

@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    list_display  = ('name', 'section', 'order')
    list_filter   = ('section',)
    ordering      = ('order',)
    readonly_fields = ('created_at', 'updated_at')


# ---------------------------------------------------------------------------
# ClassArm
# ---------------------------------------------------------------------------

@admin.register(ClassArm)
class ClassArmAdmin(admin.ModelAdmin):
    list_display  = ('__str__', 'class_level', 'name', 'capacity')
    list_filter   = ('class_level',)
    search_fields = ('name', 'class_level__name')
    ordering      = ('class_level__order', 'name')
    readonly_fields = ('created_at', 'updated_at')


# ---------------------------------------------------------------------------
# Subject
# ---------------------------------------------------------------------------

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display  = ('name', 'code', 'department', 'is_compulsory')
    list_filter   = ('is_compulsory', 'department')
    search_fields = ('name', 'code')
    filter_horizontal = ('class_levels',)
    readonly_fields = ('created_at', 'updated_at')


# ---------------------------------------------------------------------------
# SubjectAssignment
# ---------------------------------------------------------------------------

@admin.register(SubjectAssignment)
class SubjectAssignmentAdmin(admin.ModelAdmin):
    list_display  = ('teacher', 'subject', 'class_arm', 'session', 'term')
    list_filter   = ('session', 'term', 'class_arm__class_level')
    search_fields = (
        'teacher__first_name', 'teacher__last_name',
        'subject__name', 'subject__code',
    )
    autocomplete_fields = ['subject']
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'teacher', 'subject', 'class_arm', 'class_arm__class_level', 'session', 'term'
        )


# ---------------------------------------------------------------------------
# ClassTeacherAssignment
# ---------------------------------------------------------------------------

@admin.register(ClassTeacherAssignment)
class ClassTeacherAssignmentAdmin(admin.ModelAdmin):
    list_display  = ('teacher', 'class_arm', 'session')
    list_filter   = ('session', 'class_arm__class_level')
    search_fields = ('teacher__first_name', 'teacher__last_name', 'class_arm__name')
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'teacher', 'class_arm', 'class_arm__class_level', 'session'
        )
