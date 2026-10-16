from django import forms
from .models import Enrollment
from students.models import Student
from courses.models import Course

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

    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        """Block new seat-taking enrollments when the course is already full."""
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        status = cleaned_data.get('status')

        if course and status == 'ENROLLED' and course.capacity:
            # An existing ENROLLED record for the same course does not take a new seat
            holds_seat = bool(
                self.instance and self.instance.pk
                and self.instance.status == 'ENROLLED'
                and self.instance.course_id == course.pk
            )
            if not holds_seat:
                taken = Enrollment.objects.filter(course=course, status='ENROLLED').count()
                if taken >= course.capacity:
                    self.add_error(
                        'course',
                        f"This course is full — {taken}/{course.capacity} seats taken. "
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

class EnrollmentFilterForm(forms.Form):
    """Form for filtering enrollments"""
    STATUS_CHOICES = [('', '--- All Status ---')] + list(Enrollment.STATUS_CHOICES)
    
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    student = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search student...'}))
    course = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search course...'}))
