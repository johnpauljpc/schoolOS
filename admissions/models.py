from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class ApplicantStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Review'
    SCREENED = 'SCREENED', 'Screened'
    ADMITTED = 'ADMITTED', 'Admitted'
    REJECTED = 'REJECTED', 'Rejected'
    ENROLLED = 'ENROLLED', 'Enrolled'


class Applicant(TimeStampedModel):
    """An applicant who has submitted an admission application."""
    # Personal info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[('MALE', 'Male'), ('FEMALE', 'Female')])
    religion = models.CharField(max_length=50, blank=True)
    nationality = models.CharField(max_length=50, default='Nigerian')
    state_of_origin = models.CharField(max_length=50, blank=True)
    lga = models.CharField(max_length=100, blank=True, verbose_name='LGA')
    # Academic
    applying_for_class = models.ForeignKey(
        'academics.ClassLevel',
        on_delete=models.SET_NULL, null=True,
        related_name='applicants'
    )
    session = models.ForeignKey(
        'academics.AcademicSession',
        on_delete=models.SET_NULL, null=True,
        related_name='applicants'
    )
    previous_school = models.CharField(max_length=200, blank=True)
    previous_class = models.CharField(max_length=100, blank=True)
    # Guardian info
    guardian_name = models.CharField(max_length=200)
    guardian_relationship = models.CharField(max_length=50)
    guardian_phone = models.CharField(max_length=20)
    guardian_email = models.EmailField(blank=True)
    guardian_address = models.TextField(blank=True)
    # Application state
    application_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(
        max_length=15,
        choices=ApplicantStatus.choices,
        default=ApplicantStatus.PENDING
    )
    passport_photo = models.ImageField(upload_to='applicant_photos/', null=True, blank=True)
    # Review
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_applications'
    )
    review_notes = models.TextField(blank=True)
    review_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Applicant'
        verbose_name_plural = 'Applicants'

    def __str__(self):
        return f"{self.application_number} — {self.last_name}, {self.first_name}"

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p)


class Admission(TimeStampedModel):
    """
    Finalised admission record linking Applicant to a newly-created Student.
    Created when an applicant is admitted and enrolled.
    """
    applicant = models.OneToOneField(Applicant, on_delete=models.CASCADE, related_name='admission')
    student = models.OneToOneField(
        'students.Student',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='admission_record'
    )
    admitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='admissions_granted'
    )
    admission_date = models.DateField(auto_now_add=True)
    admission_letter_generated = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Admission'
        verbose_name_plural = 'Admissions'

    def __str__(self):
        return f"Admission: {self.applicant}"
