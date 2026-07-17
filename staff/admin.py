from django.contrib import admin
from .models import Staff, StaffQualification, Teacher


class QualificationInline(admin.TabularInline):
    model = StaffQualification
    extra = 0


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('staff_id', 'full_name', 'department', 'designation', 'employment_type', 'is_active')
    list_filter = ('employment_type', 'is_active', 'department')
    search_fields = ('staff_id', 'user__first_name', 'user__last_name', 'designation')
    inlines = [QualificationInline]

    def full_name(self, obj):
        return obj.user.get_full_name()
    full_name.short_description = 'Name'


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('staff', 'class_assigned', 'specialization', 'years_of_experience')
    filter_horizontal = ('subjects',)
