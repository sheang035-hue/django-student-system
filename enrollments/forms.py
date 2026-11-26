import re

from django import forms
from .models import Enrollment, current_academic_year, current_semester
from students.models import Student
from students.academics import grade_from_score
from courses.models import Course


ACADEMIC_YEAR_RE = re.compile(r'^(\d{4})-(\d{4})$')


def clean_academic_year_value(value):
    """Validate and normalise an ``YYYY-YYYY`` academic year value."""
    value = (value or '').strip()
    match = ACADEMIC_YEAR_RE.match(value)
    if not match or int(match.group(2)) != int(match.group(1)) + 1:
        raise forms.ValidationError(
            "Enter a valid academic year, for example 2026-2027."
        )
    return value

class StudentChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        eng_name = obj.user.get_full_name() if (obj.user and obj.user.get_full_name()) else (obj.user.username if obj.user else "")
        if obj.khmer_name and eng_name and obj.khmer_name != eng_name:
            return f"{obj.student_id} - {obj.khmer_name} ({eng_name})"
        elif obj.khmer_name:
            return f"{obj.student_id} - {obj.khmer_name}"
        elif eng_name:
            return f"{obj.student_id} - {eng_name}"
        return str(obj)

class CourseChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        instructor_str = f" | Prof: {obj.instructor.get_full_name() or obj.instructor.username}" if obj.instructor else ""
        return f"{obj.code} - {obj.title} ({obj.get_level_display()}){instructor_str}"

class EnrollmentForm(forms.ModelForm):
    """Form for creating and updating enrollments with searchable selections"""
    student = StudentChoiceField(
        queryset=Student.objects.select_related('user').all().order_by('student_id'),
        widget=forms.Select(attrs={
            'class': 'form-select searchable-select',
            'id': 'id_student',
        }),
        help_text="ស្វែងរកតាមអត្តលេខ, ឈ្មោះខ្មែរ, ឬឈ្មោះឡាតាំង"
    )
    course = CourseChoiceField(
        queryset=Course.objects.select_related('instructor').all().order_by('code'),
        widget=forms.Select(attrs={
            'class': 'form-select searchable-select',
            'id': 'id_course',
        }),
        help_text="ស្វែងរកតាមកូដមុខវិជ្ជា, ឈ្មោះមុខវិជ្ជា, ឬសាស្រ្តាចារ្យ"
    )
    academic_year = forms.CharField(
        max_length=9,
        initial=current_academic_year,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '2026-2027',
            'list': 'academic-year-options',
            'autocomplete': 'off',
        }),
        help_text="Academic year in the format 2026-2027",
    )
    semester = forms.ChoiceField(
        choices=Enrollment.SEMESTER_CHOICES,
        initial=current_semester,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="The same subject can be enrolled again in a different semester.",
    )

    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'academic_year', 'semester', 'status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_academic_year(self):
        return clean_academic_year_value(self.cleaned_data.get('academic_year'))

    def clean(self):
        """Block new seat-taking enrollments when the course is already full."""
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        status = cleaned_data.get('status')
        academic_year = cleaned_data.get('academic_year')
        semester = cleaned_data.get('semester')

        if course and status == 'ENROLLED' and course.capacity:
            # An existing ENROLLED record for the same course and term does not
            # take a new seat.
            holds_seat = bool(
                self.instance and self.instance.pk
                and self.instance.status == 'ENROLLED'
                and self.instance.course_id == course.pk
                and self.instance.academic_year == academic_year
                and self.instance.semester == semester
            )
            if not holds_seat:
                taken = Enrollment.objects.filter(
                    course=course,
                    status='ENROLLED',
                    academic_year=academic_year,
                    semester=semester,
                ).count()
                if taken >= course.capacity:
                    self.add_error(
                        'course',
                        f"This course is full for {semester} {academic_year} — {taken}/{course.capacity} seats taken. "
                        f"Choose another course or contact the registrar. "
                        f"(មុខវិជ្ជានេះពេញហើយ — សូមជ្រើសរើសមុខវិជ្ជាផ្សេង)"
                    )
        return cleaned_data

class GradeForm(forms.ModelForm):
    """Form for entering student grades and scores"""
    class Meta:
        model = Enrollment
        fields = ['score', 'attendance_percentage', 'notes']
        widgets = {
            'score': forms.NumberInput(attrs={'class': 'form-control', 'type': 'number', 'min': '0', 'max': '100', 'step': '0.01'}),
            'attendance_percentage': forms.NumberInput(attrs={'class': 'form-control', 'type': 'number', 'min': '0', 'max': '100', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def save(self, commit=True):
        """Recalculate the letter grade whenever a new score is saved."""
        enrollment = super().save(commit=False)
        if enrollment.score is not None:
            enrollment.grade = grade_from_score(enrollment.score) or None
        if commit:
            enrollment.save()
        return enrollment


class GradeEntryForm(forms.Form):
    """One-page, admin-only form for recording a subject score for a term."""

    student = StudentChoiceField(
        queryset=Student.objects.select_related('user').all().order_by('student_id'),
        widget=forms.Select(attrs={
            'class': 'form-select searchable-select',
            'id': 'id_student',
        }),
        help_text="Search by student ID, Khmer name, or Latin name",
    )
    course = CourseChoiceField(
        queryset=Course.objects.select_related('instructor').all().order_by('code'),
        widget=forms.Select(attrs={
            'class': 'form-select searchable-select',
            'id': 'id_course',
        }),
        help_text="Search by course code, title, or instructor",
    )
    academic_year = forms.CharField(
        max_length=9,
        initial=current_academic_year,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '2026-2027',
            'list': 'academic-year-options',
            'autocomplete': 'off',
        }),
    )
    semester = forms.ChoiceField(
        choices=Enrollment.SEMESTER_CHOICES,
        initial=current_semester,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    status = forms.ChoiceField(
        choices=Enrollment.STATUS_CHOICES,
        initial='COMPLETED',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    score = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'type': 'number',
            'min': '0',
            'max': '100',
            'step': '0.01',
            'placeholder': 'e.g. 86.50',
        }),
    )
    attendance_percentage = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'type': 'number',
            'min': '0',
            'max': '100',
            'step': '0.01',
            'placeholder': 'e.g. 95',
        }),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional note for the registrar or student record…',
        }),
    )

    def clean_academic_year(self):
        return clean_academic_year_value(self.cleaned_data.get('academic_year'))

class EnrollmentFilterForm(forms.Form):
    """Form for filtering enrollments"""
    STATUS_CHOICES = [('', '--- All Status ---')] + list(Enrollment.STATUS_CHOICES)
    
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    student = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search student...'}))
    course = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search course...'}))
