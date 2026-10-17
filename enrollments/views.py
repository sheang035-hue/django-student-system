import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponse
from django.core.paginator import Paginator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg
from django.urls import reverse_lazy
from .models import Enrollment
from .forms import EnrollmentForm, GradeForm, EnrollmentFilterForm

# Function-Based Views (FBV)

@login_required
def enrollment_list(request):
    """List all enrollments with filtering options, KPI chips, and pagination"""
    enrollments_qs = Enrollment.objects.select_related('student__user', 'course')
    form = EnrollmentFilterForm(request.GET or None)
    
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '').strip()
    
    if search:
        enrollments_qs = enrollments_qs.filter(
            Q(student__student_id__icontains=search) |
            Q(student__khmer_name__icontains=search) |
            Q(student__user__first_name__icontains=search) |
            Q(student__user__last_name__icontains=search) |
            Q(course__code__icontains=search) |
            Q(course__title__icontains=search)
        )
    
    if status:
        enrollments_qs = enrollments_qs.filter(status=status)
    elif form.is_valid() and form.cleaned_data.get('status'):
        enrollments_qs = enrollments_qs.filter(status=form.cleaned_data['status'])
        
    enrollments_qs = enrollments_qs.order_by('-enrollment_date')
    total_count = Enrollment.objects.count()
    completed_count = Enrollment.objects.filter(status='COMPLETED').count()
    
    paginator = Paginator(enrollments_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'enrollments': page_obj,
        'page_obj': page_obj,
        'form': form,
        'total_count': total_count,
        'completed_count': completed_count,
    }
    return render(request, 'enrollments/enrollment_list.html', context)


@login_required
def export_enrollments_csv(request):
    """Export filtered or all course enrollments to CSV spreadsheet with UTF-8 BOM."""
    enrollments_qs = Enrollment.objects.select_related('student__user', 'course')
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '').strip()
    
    if search:
        enrollments_qs = enrollments_qs.filter(
            Q(student__student_id__icontains=search) |
            Q(student__khmer_name__icontains=search) |
            Q(student__user__first_name__icontains=search) |
            Q(student__user__last_name__icontains=search) |
            Q(course__code__icontains=search) |
            Q(course__title__icontains=search)
        )
    if status:
        enrollments_qs = enrollments_qs.filter(status=status)
        
    enrollments_qs = enrollments_qs.order_by('-enrollment_date')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="bbu_course_enrollments.csv"'
    
    # Write UTF-8 BOM for Microsoft Excel Khmer compatibility
    response.write('\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    writer.writerow([
        'Student ID',
        'Student Name (Khmer)',
        'Student Name (Latin)',
        'Course Code',
        'Course Title',
        'Credits',
        'Score',
        'Grade',
        'Attendance (%)',
        'Status',
        'Enrollment Date'
    ])
    
    for e in enrollments_qs:
        writer.writerow([
            e.student.student_id,
            e.student.khmer_name or '',
            e.student.user.get_full_name() or e.student.user.username,
            e.course.code,
            e.course.title,
            e.course.credits,
            e.score if e.score is not None else '',
            e.grade or '',
            e.attendance_percentage or '',
            e.get_status_display(),
            e.enrollment_date.strftime('%Y-%m-%d') if e.enrollment_date else ''
        ])
    return response

@login_required
def enrollment_detail(request, pk):
    """Display detailed information about an enrollment"""
    enrollment = get_object_or_404(Enrollment, pk=pk)
    
    context = {'enrollment': enrollment}
    return render(request, 'enrollments/enrollment_detail.html', context)

@login_required
def enrollment_create(request):
    """Create a new enrollment"""
    if request.method == 'POST':
        form = EnrollmentForm(request.POST)
        if form.is_valid():
            enrollment = form.save()
            return redirect('enrollments:enrollment_detail', pk=enrollment.pk)
    else:
        form = EnrollmentForm()
    
    context = {'form': form, 'title': 'Create Enrollment'}
    return render(request, 'enrollments/enrollment_form.html', context)

@login_required
def enrollment_update(request, pk):
    """Update enrollment information"""
    enrollment = get_object_or_404(Enrollment, pk=pk)
    
    if request.method == 'POST':
        form = EnrollmentForm(request.POST, instance=enrollment)
        if form.is_valid():
            form.save()
            return redirect('enrollments:enrollment_detail', pk=enrollment.pk)
    else:
        form = EnrollmentForm(instance=enrollment)
    
    context = {'form': form, 'enrollment': enrollment, 'title': 'Update Enrollment'}
    return render(request, 'enrollments/enrollment_form.html', context)

@login_required
def enrollment_delete(request, pk):
    """Delete an enrollment"""
    enrollment = get_object_or_404(Enrollment, pk=pk)
    
    if request.method == 'POST':
        enrollment.delete()
        return redirect('enrollments:enrollment_list')
    
    context = {'enrollment': enrollment}
    return render(request, 'enrollments/enrollment_confirm_delete.html', context)

@login_required
def add_grade(request, pk):
    """Add or update grade for an enrollment"""
    enrollment = get_object_or_404(Enrollment, pk=pk)
    
    if request.method == 'POST':
        form = GradeForm(request.POST, instance=enrollment)
        if form.is_valid():
            form.save()
            return redirect('enrollments:enrollment_detail', pk=enrollment.pk)
    else:
        form = GradeForm(instance=enrollment)
    
    context = {'form': form, 'enrollment': enrollment}
    return render(request, 'enrollments/add_grade.html', context)

@login_required
def student_transcript(request, student_id):
    """Generate transcript for a student showing all enrollments and grades"""
    from students.models import Student
    
    student = Student.objects.filter(student_id=student_id).first()
    if not student and str(student_id).isdigit():
        student = Student.objects.filter(pk=int(student_id)).first()
    if not student:
        raise Http404("Student not found")
        
    enrollments = list(student.enrollments.select_related('course').all())
    
    # Grading points reference mapping (MoEYS Standard)
    grade_points_map = {
        'A': 4.00,
        'B+': 3.50,
        'B': 3.00,
        'C+': 2.50,
        'C': 2.00,
        'D': 1.50,
        'F': 0.00,
    }
    
    course_khmer_map = {
        'CS101': 'សេចក្តីផ្តើមវិទ្យាសាស្ត្រកុំព្យូទ័រ',
        'WD201': 'មូលដ្ឋានគ្រឹះនៃការអភិវឌ្ឍវេបសាយ',
        'DB202': 'ប្រព័ន្ធគ្រប់គ្រងមូលដ្ឋានទិន្នន័យ',
        'PY204': 'ការសរសេរកម្មវិធី Python',
        'NET203': 'ប្រព័ន្ធបណ្តាញកុំព្យូទ័រ',
    }
    
    # Enrich enrollment items with grade points, credit points, and Khmer titles
    total_credit_points = 0.0
    for e in enrollments:
        # Determine letter grade & grade point
        grade = (e.grade or '').strip().upper()
        if not grade and e.score is not None:
            if e.score >= 85: grade = 'A'
            elif e.score >= 80: grade = 'B+'
            elif e.score >= 70: grade = 'B'
            elif e.score >= 65: grade = 'C+'
            elif e.score >= 50: grade = 'C'
            elif e.score >= 45: grade = 'D'
            else: grade = 'F'
            e.grade = grade
            
        gp = grade_points_map.get(grade, 0.0)
        e.grade_point = gp
        credits = e.course.credits if (e.course and e.course.credits) else 0
        
        if e.status == 'COMPLETED':
            cp = round(credits * gp, 2)
            e.credit_points = cp
            total_credit_points += cp
            e.is_passed = grade != 'F' and (e.score is None or e.score >= 50)
        else:
            e.credit_points = 0.0
            e.is_passed = False
        # Clean separation of English title and Khmer title to avoid duplication
        raw_title = e.course.title if e.course else ''
        if '(' in raw_title and ')' in raw_title:
            en_title = raw_title[:raw_title.find('(')].strip()
            kh_title = raw_title[raw_title.find('(')+1:raw_title.rfind(')')].strip()
        else:
            en_title = raw_title
            kh_title = course_khmer_map.get(e.course.code, '') if e.course else ''
        e.clean_en_title = en_title
        e.clean_kh_title = kh_title

    completed_courses = [e for e in enrollments if e.status == 'COMPLETED' and e.score is not None]
    average_score = sum(float(e.score) for e in completed_courses) / len(completed_courses) if completed_courses else 0
    total_credits = sum(e.course.credits for e in enrollments if e.course and e.course.credits)
    earned_credits = sum(e.course.credits for e in completed_courses if e.course and e.course.credits)
    
    # Calculate or confirm GPA
    calculated_gpa = round(total_credit_points / earned_credits, 2) if earned_credits > 0 else 0.0
    effective_gpa = float(student.gpa) if float(student.gpa) > 0 else calculated_gpa
    
    # Academic Standing Classification
    if effective_gpa >= 3.80:
        standing_en = "Highest Distinction (Summa Cum Laude)"
        standing_kh = "ល្អប្រសើរដាច់គេ"
        standing_badge = "success"
    elif effective_gpa >= 3.50:
        standing_en = "High Distinction (Magna Cum Laude)"
        standing_kh = "ល្អប្រសើរ"
        standing_badge = "success"
    elif effective_gpa >= 3.00:
        standing_en = "Distinction (Cum Laude)"
        standing_kh = "ល្អណាស់"
        standing_badge = "primary"
    elif effective_gpa >= 2.50:
        standing_en = "Good Standing"
        standing_kh = "ល្អបង្គួរ"
        standing_badge = "info"
    elif effective_gpa >= 2.00:
        standing_en = "Satisfactory"
        standing_kh = "មធ្យម"
        standing_badge = "secondary"
    else:
        standing_en = "Academic Probation"
        standing_kh = "ក្រោមស្តង់ដារ"
        standing_badge = "warning"
    
    import datetime
    today = datetime.date.today()
    khmer_months = [
        '', 'មករា', 'កុម្ភៈ', 'មីនា', 'មេសា', 'ឧសភា', 'មិថុនា',
        'កក្កដា', 'សីហា', 'កញ្ញា', 'តុលា', 'វិច្ឆិកា', 'ធ្នូ'
    ]
    english_months = [
        '', 'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    issue_date_kh = f"ថ្ងៃទី {today.day:02d} ខែ {khmer_months[today.month]} ឆ្នាំ {today.year}"
    issue_date_en = f"{today.day:02d} {english_months[today.month]} {today.year}"
    
    context = {
        'student': student,
        'enrollments': enrollments,
        'average_score': round(average_score, 2),
        'total_courses': len(enrollments),
        'completed_courses': len(completed_courses),
        'total_credits': total_credits,
        'earned_credits': earned_credits,
        'total_credit_points': round(total_credit_points, 2),
        'effective_gpa': f"{effective_gpa:.2f}",
        'standing_en': standing_en,
        'standing_kh': standing_kh,
        'standing_badge': standing_badge,
        'transcript_no': f"BBU-TR-2026-{student.student_id}",
        'issue_date_kh': issue_date_kh,
        'issue_date_en': issue_date_en,
    }
    return render(request, 'enrollments/student_transcript.html', context)

# Class-Based Views (CBV)

class EnrollmentListView(LoginRequiredMixin, ListView):
    """Class-based view for listing enrollments"""
    model = Enrollment
    template_name = 'enrollments/enrollment_list.html'
    context_object_name = 'enrollments'
    paginate_by = 20
    
    def get_queryset(self):
        return Enrollment.objects.select_related('student', 'course').order_by('-enrollment_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = EnrollmentFilterForm(self.request.GET or None)
        return context

class EnrollmentDetailView(LoginRequiredMixin, DetailView):
    """Class-based view for enrollment details"""
    model = Enrollment
    template_name = 'enrollments/enrollment_detail.html'
    context_object_name = 'enrollment'

class EnrollmentCreateView(LoginRequiredMixin, CreateView):
    """Class-based view for creating a new enrollment"""
    model = Enrollment
    form_class = EnrollmentForm
    template_name = 'enrollments/enrollment_form.html'
    success_url = reverse_lazy('enrollments:enrollment_list')

class EnrollmentUpdateView(LoginRequiredMixin, UpdateView):
    """Class-based view for updating enrollment information"""
    model = Enrollment
    form_class = EnrollmentForm
    template_name = 'enrollments/enrollment_form.html'
    success_url = reverse_lazy('enrollments:enrollment_list')

class EnrollmentDeleteView(LoginRequiredMixin, DeleteView):
    """Class-based view for deleting an enrollment"""
    model = Enrollment
    template_name = 'enrollments/enrollment_confirm_delete.html'
    success_url = reverse_lazy('enrollments:enrollment_list')
