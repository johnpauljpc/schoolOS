"""
academics/models.py

All academic-structure models for SchoolOS.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class TermName(models.TextChoices):
    FIRST  = 'FIRST',  'First Term'
    SECOND = 'SECOND', 'Second Term'
    THIRD  = 'THIRD',  'Third Term'


class SectionChoice(models.TextChoices):
    JUNIOR = 'JUNIOR', 'Junior Secondary'
    SENIOR = 'SENIOR', 'Senior Secondary'


# ---------------------------------------------------------------------------
# AcademicSession
# ---------------------------------------------------------------------------

class AcademicSession(TimeStampedModel):
    """Represents a school academic year, e.g. '2024/2025'."""

    name       = models.CharField(max_length=20, unique=True, verbose_name=_('Session Name'))
    start_date = models.DateField(verbose_name=_('Start Date'))
    end_date   = models.DateField(verbose_name=_('End Date'))
    is_current = models.BooleanField(default=False, verbose_name=_('Is Current Session'))

    class Meta:
        ordering = ['-start_date']
        verbose_name        = _('Academic Session')
        verbose_name_plural = _('Academic Sessions')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Ensure only one session is current at a time."""
        if self.is_current:
            AcademicSession.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_current(cls):
        return cls.objects.filter(is_current=True).first()


# ---------------------------------------------------------------------------
# AcademicTerm
# ---------------------------------------------------------------------------

class AcademicTerm(TimeStampedModel):
    """A term within an academic session."""

    session          = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='terms',
        verbose_name=_('Academic Session'),
    )
    name             = models.CharField(
        max_length=10,
        choices=TermName.choices,
        verbose_name=_('Term'),
    )
    start_date       = models.DateField(verbose_name=_('Start Date'))
    end_date         = models.DateField(verbose_name=_('End Date'))
    is_current       = models.BooleanField(default=False, verbose_name=_('Is Current Term'))
    next_term_begins = models.DateField(
        null=True, blank=True,
        verbose_name=_('Next Term Begins'),
    )

    class Meta:
        ordering            = ['session', 'name']
        unique_together     = ('session', 'name')
        verbose_name        = _('Academic Term')
        verbose_name_plural = _('Academic Terms')

    def __str__(self):
        return f"{self.get_name_display()} — {self.session}"

    def save(self, *args, **kwargs):
        """Ensure only one term is current at a time."""
        if self.is_current:
            AcademicTerm.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_current(cls):
        return cls.objects.filter(is_current=True).select_related('session').first()


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------

class Department(TimeStampedModel):
    """School department grouping subjects/staff."""

    name        = models.CharField(max_length=100, unique=True, verbose_name=_('Department Name'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    head        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='headed_departments',
        verbose_name=_('Department Head'),
        limit_choices_to={'is_active': True},
    )

    class Meta:
        ordering            = ['name']
        verbose_name        = _('Department')
        verbose_name_plural = _('Departments')

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# ClassLevel
# ---------------------------------------------------------------------------

class ClassLevel(TimeStampedModel):
    """Represents a school class level, e.g. JSS1, SS2."""

    name    = models.CharField(max_length=20, unique=True, verbose_name=_('Class Level'))
    order   = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_('Order'),
        help_text=_('Lower numbers appear first (e.g. JSS1=1, SS3=6).'),
    )
    section = models.CharField(
        max_length=10,
        choices=SectionChoice.choices,
        verbose_name=_('Section'),
    )

    class Meta:
        ordering            = ['order']
        verbose_name        = _('Class Level')
        verbose_name_plural = _('Class Levels')

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# ClassArm
# ---------------------------------------------------------------------------

class ClassArm(TimeStampedModel):
    """An arm/stream within a class level, e.g. JSS1A, SS2 Science."""

    class_level = models.ForeignKey(
        ClassLevel,
        on_delete=models.CASCADE,
        related_name='arms',
        verbose_name=_('Class Level'),
    )
    name     = models.CharField(max_length=20, verbose_name=_('Arm Name'))
    capacity = models.PositiveSmallIntegerField(
        default=40,
        verbose_name=_('Capacity'),
    )

    class Meta:
        ordering            = ['class_level__order', 'name']
        unique_together     = ('class_level', 'name')
        verbose_name        = _('Class Arm')
        verbose_name_plural = _('Class Arms')

    def __str__(self):
        return f"{self.class_level} {self.name}"


# ---------------------------------------------------------------------------
# Subject
# ---------------------------------------------------------------------------

class Subject(TimeStampedModel):
    """A school subject offered in one or more class levels."""

    name         = models.CharField(max_length=100, verbose_name=_('Subject Name'))
    code         = models.CharField(
        max_length=10, unique=True,
        verbose_name=_('Subject Code'),
        help_text=_('Short unique code, e.g. MTH, ENG, BIO.'),
    )
    department   = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='subjects',
        verbose_name=_('Department'),
    )
    class_levels = models.ManyToManyField(
        ClassLevel,
        blank=True,
        related_name='subjects',
        verbose_name=_('Class Levels'),
    )
    is_compulsory = models.BooleanField(default=True, verbose_name=_('Compulsory'))
    description   = models.TextField(blank=True, verbose_name=_('Description'))

    class Meta:
        ordering            = ['name']
        verbose_name        = _('Subject')
        verbose_name_plural = _('Subjects')

    def __str__(self):
        return f"{self.name} ({self.code})"


# ---------------------------------------------------------------------------
# SubjectAssignment
# ---------------------------------------------------------------------------

class SubjectAssignment(TimeStampedModel):
    """Maps a teacher → subject → class arm for a given session/term."""

    teacher   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subject_assignments',
        verbose_name=_('Teacher'),
        limit_choices_to={'role__in': ['TEACHER', 'CLASS_TEACHER']},
    )
    subject   = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('Subject'),
    )
    class_arm = models.ForeignKey(
        ClassArm,
        on_delete=models.CASCADE,
        related_name='subject_assignments',
        verbose_name=_('Class Arm'),
    )
    session   = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='subject_assignments',
        verbose_name=_('Session'),
    )
    term      = models.ForeignKey(
        AcademicTerm,
        on_delete=models.CASCADE,
        related_name='subject_assignments',
        verbose_name=_('Term'),
    )

    class Meta:
        unique_together     = ('teacher', 'subject', 'class_arm', 'session', 'term')
        ordering            = ['session', 'term', 'class_arm', 'subject']
        verbose_name        = _('Subject Assignment')
        verbose_name_plural = _('Subject Assignments')

    def __str__(self):
        return (
            f"{self.teacher.get_full_name()} → {self.subject.code} "
            f"[{self.class_arm}] ({self.term} / {self.session})"
        )


# ---------------------------------------------------------------------------
# ClassTeacherAssignment
# ---------------------------------------------------------------------------

class ClassTeacherAssignment(TimeStampedModel):
    """Assigns one form/class teacher to a class arm per session."""

    teacher   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='class_teacher_assignments',
        verbose_name=_('Class Teacher'),
        limit_choices_to={'is_active': True},
    )
    class_arm = models.ForeignKey(
        ClassArm,
        on_delete=models.CASCADE,
        related_name='class_teacher_assignments',
        verbose_name=_('Class Arm'),
    )
    session   = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='class_teacher_assignments',
        verbose_name=_('Session'),
    )

    class Meta:
        unique_together     = ('class_arm', 'session')
        ordering            = ['session', 'class_arm']
        verbose_name        = _('Class Teacher Assignment')
        verbose_name_plural = _('Class Teacher Assignments')

    def __str__(self):
        return f"{self.teacher.get_full_name()} → {self.class_arm} ({self.session})"
