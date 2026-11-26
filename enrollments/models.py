from datetime import date

from django.db import models
from students.models import Student
from courses.models import Course
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator


def current_academic_year():
    """Return the active BBU academic year, e.g. ``2026-2027`` (Oct–Sep cycle)."""
    today = date.today()
    start = today.year if today.month >= 10 else today.year - 1
    return f"{start}-{start + 1}"


def current_semester():
    """Return the semester that matches today's month."""
    month = date.today().month
    if 2 <= month <= 7:
        return 'S2'
    if 8 <= month <= 9:
        return 'SUM'
    return 'S1'


class Enrollment(models.Model):
    """Model to store student course enrollment information"""
    
    STATUS_CHOICES = [
        ('ENROLLED', 'Enrolled'),
        ('COMPLETED', 'Completed'),
        ('DROPPED', 'Dropped'),
        ('SUSPENDED', 'Suspended'),
    ]

    SEMESTER_CHOICES = [
        ('S1', 'Semester 1'),
        ('S2', 'Semester 2'),
        ('SUM', 'Summer'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    academic_year = models.CharField(
        max_length=9,
        default=current_academic_year,
        help_text="Academic year in the format 2026-2027",
    )
    semester = models.CharField(
        max_length=3,
        choices=SEMESTER_CHOICES,
        default=current_semester,
        help_text="Term in which the subject is taken",
    )
    enrollment_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ENROLLED')
    grade = models.CharField(max_length=2, blank=True, null=True, help_text="Letter grade (A, B+, B, C+, C, D, F)")
    score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True,
                               validators=[MinValueValidator(0), MaxValueValidator(100)])
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                               validators=[MinValueValidator(0), MaxValueValidator(100)])
    completed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # A subject can be taken once per semester; repeating it in a later
        # semester creates a new record instead of overwriting the old grade.
        unique_together = ('student', 'course', 'academic_year', 'semester')
        ordering = ['-academic_year', '-semester', '-enrollment_date', '-id']
        verbose_name_plural = "Enrollments"
        indexes = [
            models.Index(fields=['student', 'course']),
            models.Index(fields=['status']),
            models.Index(fields=['academic_year', 'semester']),
        ]

    def __str__(self):
        return f"{self.student.student_id} - {self.course.code}"

    def get_absolute_url(self):
        return reverse('enrollments:enrollment_detail', kwargs={'pk': self.pk})

    @property
    def term_label(self):
        return f"{self.get_semester_display()} · {self.academic_year}"

    def calculate_grade(self):
        """Calculate the BBU letter grade (A, B+, B, C+, C, D, F) from the score."""
        if self.score is None:
            return None
        from students.academics import grade_from_score
        return grade_from_score(self.score) or None
    
    def save(self, *args, **kwargs):
        """Automatically calculate grade before saving when none is recorded."""
        if self.score is not None and not self.grade:
            self.grade = self.calculate_grade()
        super().save(*args, **kwargs)
