from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import TimeStampedModel


class GradeConfig(models.Model):
    """
    Configurable grade boundaries.
    e.g. 70-100 → A1 (Excellent), 60-69 → B2, etc.
    """
    min_score = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    max_score = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    grade = models.CharField(max_length=5)       # A1, B2, C4, F9 …
    remark = models.CharField(max_length=50)     # Excellent, Very Good, Pass, Fail …
    point = models.DecimalField(max_digits=4, decimal_places=2, default=0)  # GPA points
    is_pass = models.BooleanField(default=True)

    class Meta:
        ordering = ['-min_score']
        verbose_name = 'Grade Configuration'
        verbose_name_plural = 'Grade Configurations'

    def __str__(self):
        return f"{self.grade}: {self.min_score}–{self.max_score} ({self.remark})"

    @classmethod
    def get_grade_for_score(cls, score):
        """Return the GradeConfig that matches a given score."""
        return cls.objects.filter(
            min_score__lte=score, max_score__gte=score
        ).first()


class Assessment(TimeStampedModel):
    """Continuous Assessment scores (CA1, CA2, CA3) for a student/subject/term."""
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='assessments')
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE)
    class_arm = models.ForeignKey('academics.ClassArm', on_delete=models.CASCADE)
    session = models.ForeignKey('academics.AcademicSession', on_delete=models.CASCADE)
    term = models.ForeignKey('academics.AcademicTerm', on_delete=models.CASCADE)
    ca1 = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        verbose_name='CA 1 (20)'
    )
    ca2 = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        verbose_name='CA 2 (20)'
    )
    ca3 = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        verbose_name='CA 3 (20)'
    )
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        unique_together = ('student', 'subject', 'session', 'term')
        verbose_name = 'Assessment'
        verbose_name_plural = 'Assessments'

    def __str__(self):
        return f"{self.student} — {self.subject} [{self.session}/{self.term}]"

    @property
    def total_ca(self):
        return self.ca1 + self.ca2 + self.ca3


class ExaminationScore(TimeStampedModel):
    """Examination (exam) score for a student/subject/term."""
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='exam_scores')
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE)
    class_arm = models.ForeignKey('academics.ClassArm', on_delete=models.CASCADE)
    session = models.ForeignKey('academics.AcademicSession', on_delete=models.CASCADE)
    term = models.ForeignKey('academics.AcademicTerm', on_delete=models.CASCADE)
    score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(60)],
        verbose_name='Exam Score (60)'
    )
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        unique_together = ('student', 'subject', 'session', 'term')
        verbose_name = 'Examination Score'
        verbose_name_plural = 'Examination Scores'

    def __str__(self):
        return f"{self.student} — {self.subject} Exam: {self.score}"


class Result(TimeStampedModel):
    """
    Computed result for a student's subject in a session/term.
    Total = CA (40) + Exam (60) = 100
    """
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='results')
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE)
    class_arm = models.ForeignKey('academics.ClassArm', on_delete=models.CASCADE)
    session = models.ForeignKey('academics.AcademicSession', on_delete=models.CASCADE)
    term = models.ForeignKey('academics.AcademicTerm', on_delete=models.CASCADE)
    # Scores
    ca_total = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    exam_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    grade = models.CharField(max_length=5, blank=True)
    remark = models.CharField(max_length=50, blank=True)
    position = models.PositiveSmallIntegerField(null=True, blank=True)
    # Status
    is_approved = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_results'
    )
    approval_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'subject', 'session', 'term')
        ordering = ['-session__name', 'subject__name']
        verbose_name = 'Result'
        verbose_name_plural = 'Results'

    def __str__(self):
        return f"{self.student} — {self.subject}: {self.total_score} ({self.grade})"

    def compute(self):
        """Compute total, grade, and remark from linked Assessment and ExaminationScore."""
        try:
            assessment = Assessment.objects.get(
                student=self.student, subject=self.subject,
                session=self.session, term=self.term
            )
            self.ca_total = assessment.total_ca
        except Assessment.DoesNotExist:
            self.ca_total = 0
        try:
            exam = ExaminationScore.objects.get(
                student=self.student, subject=self.subject,
                session=self.session, term=self.term
            )
            self.exam_score = exam.score
        except ExaminationScore.DoesNotExist:
            self.exam_score = 0

        self.total_score = self.ca_total + self.exam_score
        grade_config = GradeConfig.get_grade_for_score(int(self.total_score))
        if grade_config:
            self.grade = grade_config.grade
            self.remark = grade_config.remark
        self.save()
        return self


class ExaminationTimetable(TimeStampedModel):
    """Scheduled examination slot."""
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE)
    class_arm = models.ForeignKey('academics.ClassArm', on_delete=models.CASCADE)
    session = models.ForeignKey('academics.AcademicSession', on_delete=models.CASCADE)
    term = models.ForeignKey('academics.AcademicTerm', on_delete=models.CASCADE)
    exam_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['exam_date', 'start_time']
        verbose_name = 'Examination Timetable'
        verbose_name_plural = 'Examination Timetables'

    def __str__(self):
        return f"{self.subject} — {self.class_arm} — {self.exam_date}"


class ClassTimetable(TimeStampedModel):
    """Weekly class timetable slot."""
    DAY_CHOICES = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'),
    ]
    class_arm = models.ForeignKey('academics.ClassArm', on_delete=models.CASCADE, related_name='timetable')
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True
    )
    session = models.ForeignKey('academics.AcademicSession', on_delete=models.CASCADE)
    term = models.ForeignKey('academics.AcademicTerm', on_delete=models.CASCADE)
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['day_of_week', 'start_time']
        verbose_name = 'Class Timetable'
        verbose_name_plural = 'Class Timetables'

    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time} — {self.class_arm} {self.subject}"
