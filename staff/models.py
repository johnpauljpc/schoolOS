from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class EmploymentType(models.TextChoices):
    FULL_TIME = 'FULL_TIME', 'Full-Time'
    PART_TIME = 'PART_TIME', 'Part-Time'
    CONTRACT = 'CONTRACT', 'Contract'
    VOLUNTEER = 'VOLUNTEER', 'Volunteer'


class QualificationLevel(models.TextChoices):
    WAEC = 'WAEC', 'WAEC/NECO'
    OND = 'OND', 'OND'
    HND = 'HND', 'HND'
    BSC = 'BSC', 'B.Sc / B.Ed'
    MSC = 'MSC', 'M.Sc / M.Ed'
    PHD = 'PHD', 'Ph.D'
    OTHER = 'OTHER', 'Other'


class Staff(TimeStampedModel):
    """Core staff profile linked to a User account."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_profile'
    )
    staff_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(
        'academics.Department',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='staff_members'
    )
    designation = models.CharField(max_length=100, blank=True)
    employment_type = models.CharField(
        max_length=15,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME
    )
    date_joined = models.DateField(null=True, blank=True)
    date_left = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=20, blank=True)
    account_name = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['staff_id']
        verbose_name = 'Staff Member'
        verbose_name_plural = 'Staff Members'

    def __str__(self):
        return f"{self.user.full_name} ({self.staff_id})"

    @property
    def full_name(self):
        return self.user.full_name


class StaffQualification(TimeStampedModel):
    """Academic/professional qualifications of a staff member."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='qualifications')
    level = models.CharField(max_length=10, choices=QualificationLevel.choices)
    institution = models.CharField(max_length=200)
    course = models.CharField(max_length=200)
    year_obtained = models.PositiveSmallIntegerField(null=True, blank=True)
    certificate = models.FileField(upload_to='staff_certificates/', null=True, blank=True)

    class Meta:
        ordering = ['-year_obtained']
        verbose_name = 'Qualification'
        verbose_name_plural = 'Qualifications'

    def __str__(self):
        return f"{self.staff} — {self.get_level_display()} from {self.institution}"


class Teacher(models.Model):
    """
    Extended profile for staff members who are teachers.
    One-to-one with Staff.
    """
    staff = models.OneToOneField(Staff, on_delete=models.CASCADE, related_name='teacher_profile')
    subjects = models.ManyToManyField('academics.Subject', blank=True, related_name='teachers')
    class_assigned = models.ForeignKey(
        'academics.ClassArm',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='class_teacher',
        help_text='The class this teacher is a form/class teacher for.'
    )
    specialization = models.CharField(max_length=200, blank=True)
    years_of_experience = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Teacher'
        verbose_name_plural = 'Teachers'

    def __str__(self):
        return f"Teacher: {self.staff.full_name}"
