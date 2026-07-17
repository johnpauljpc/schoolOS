from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class StudentStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    GRADUATED = 'GRADUATED', 'Graduated'
    WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
    TRANSFERRED = 'TRANSFERRED', 'Transferred'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    DECEASED = 'DECEASED', 'Deceased'


class BloodGroup(models.TextChoices):
    A_POS = 'A+', 'A+'
    A_NEG = 'A-', 'A-'
    B_POS = 'B+', 'B+'
    B_NEG = 'B-', 'B-'
    AB_POS = 'AB+', 'AB+'
    AB_NEG = 'AB-', 'AB-'
    O_POS = 'O+', 'O+'
    O_NEG = 'O-', 'O-'
    UNKNOWN = 'UNKNOWN', 'Unknown'


class Student(TimeStampedModel):
    """Core student profile linked to a User account."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    admission_number = models.CharField(max_length=20, unique=True)
    class_enrolled = models.ForeignKey(
        'academics.ClassArm',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='students'
    )
    date_admitted = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=15,
        choices=StudentStatus.choices,
        default=StudentStatus.ACTIVE
    )
    religion = models.CharField(max_length=50, blank=True)
    nationality = models.CharField(max_length=50, default='Nigerian')
    state_of_origin = models.CharField(max_length=50, blank=True)
    lga = models.CharField(max_length=100, blank=True, verbose_name='LGA')
    previous_school = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['admission_number']
        verbose_name = 'Student'
        verbose_name_plural = 'Students'

    def __str__(self):
        return f"{self.user.full_name} ({self.admission_number})"

    @property
    def full_name(self):
        return self.user.full_name

    @property
    def email(self):
        return self.user.email


class Parent(TimeStampedModel):
    """Parent/Guardian linked to a User account and one or more students."""
    RELATIONSHIP_CHOICES = [
        ('FATHER', 'Father'),
        ('MOTHER', 'Mother'),
        ('GUARDIAN', 'Guardian'),
        ('SIBLING', 'Sibling'),
        ('OTHER', 'Other'),
    ]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='parent_profile'
    )
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    occupation = models.CharField(max_length=100, blank=True)
    office_address = models.TextField(blank=True)
    students = models.ManyToManyField(Student, related_name='parents', blank=True)

    class Meta:
        verbose_name = 'Parent/Guardian'
        verbose_name_plural = 'Parents/Guardians'

    def __str__(self):
        return f"{self.user.full_name} ({self.get_relationship_display()})"


class Enrollment(TimeStampedModel):
    """Records a student's enrollment in a session/term/class."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    session = models.ForeignKey('academics.AcademicSession', on_delete=models.CASCADE)
    term = models.ForeignKey('academics.AcademicTerm', on_delete=models.CASCADE)
    class_arm = models.ForeignKey('academics.ClassArm', on_delete=models.CASCADE)
    date_enrolled = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'session', 'term')
        ordering = ['-session__name', '-term__name']
        verbose_name = 'Enrollment'
        verbose_name_plural = 'Enrollments'

    def __str__(self):
        return f"{self.student} — {self.session} {self.term}"


class MedicalInfo(models.Model):
    """Medical information for a student."""
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='medical_info')
    blood_group = models.CharField(
        max_length=10,
        choices=BloodGroup.choices,
        default=BloodGroup.UNKNOWN
    )
    genotype = models.CharField(max_length=10, blank=True)
    allergies = models.TextField(blank=True)
    medical_conditions = models.TextField(blank=True)
    medications = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    doctor_name = models.CharField(max_length=100, blank=True)
    doctor_phone = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'Medical Information'
        verbose_name_plural = 'Medical Information'

    def __str__(self):
        return f"Medical Info — {self.student}"


class StudentDocument(TimeStampedModel):
    """Documents attached to a student record."""
    DOC_TYPE_CHOICES = [
        ('BIRTH_CERT', 'Birth Certificate'),
        ('PASSPORT', 'Passport Photo'),
        ('RESULT', 'Previous Result'),
        ('MEDICAL', 'Medical Report'),
        ('ADMISSION_LETTER', 'Admission Letter'),
        ('OTHER', 'Other'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='student_documents/')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Student Document'
        verbose_name_plural = 'Student Documents'

    def __str__(self):
        return f"{self.student} — {self.get_doc_type_display()}"
