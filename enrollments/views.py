import csv
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponse
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg
from django.urls import reverse_lazy
from students.academics import summarize_academics, grade_from_score
from .models import Enrollment, current_academic_year, current_semester
from student_system.permissions import staff_required
from .forms import EnrollmentForm, GradeForm, EnrollmentFilterForm, GradeEntryForm

# Function-Based Views (FBV)


def _academic_year_suggestions():
    """Existing years plus the active year, newest first."""
    years = set(
        Enrollment.objects.exclude(academic_year='')
        .values_list('academic_year', flat=True)
    )
    years.add(current_academic_year())
    return sorted(years, reverse=True)

@login_required
def enrollment_list(request):
    """List all enrollments with filtering options, KPI chips, and pagination"""
    enrollments_qs = Enrollment.objects.select_related('student__user', 'course')
    form = EnrollmentFilterForm(request.GET or None)
    
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '').strip()
    academic_year = request.GET.get('academic_year', '').strip()
    semester = request.GET.get('semester', '').strip()
    
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

    if academic_year:
        enrollments_qs = enrollments_qs.filter(academic_year=academic_year)
    if semester:
        enrollments_qs = enrollments_qs.filter(semester=semester)
        
    enrollments_qs = enrollments_qs.order_by(
        '-academic_year', '-semester', '-enrollment_date', '-id'
    )
    total_count = Enrollment.objects.count()
    completed_count = Enrollment.objects.filter(status='COMPLETED').count()
    in_progress_count = Enrollment.objects.filter(status='ENROLLED').count()
    graded_count = (
        Enrollment.objects.exclude(grade__isnull=True)
        .exclude(grade='')
        .count()
    )
    academic_years = (
        Enrollment.objects.exclude(academic_year='')
        .values_list('academic_year', flat=True)
        .distinct()
        .order_by('-academic_year')
    )
    
    paginator = Paginator(enrollments_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'enrollments': page_obj,
        'page_obj': page_obj,
        'form': form,
        'total_count': total_count,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'graded_count': graded_count,
        'academic_years': academic_years,
        'semester_choices': Enrollment.SEMESTER_CHOICES,
        'selected_academic_year': academic_year,
        'selected_semester': semester,
    }
    return render(request, 'enrollments/enrollment_list.html', context)


@login_required
def export_enrollments_csv(request):
    """Export filtered or all course enrollments to CSV spreadsheet with UTF-8 BOM."""
    enrollments_qs = Enrollment.objects.select_related('student__user', 'course')
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '').strip()
    academic_year = request.GET.get('academic_year', '').strip()
    semester = request.GET.get('semester', '').strip()
    
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
    if academic_year:
        enrollments_qs = enrollments_qs.filter(academic_year=academic_year)
    if semester:
        enrollments_qs = enrollments_qs.filter(semester=semester)
        
    enrollments_qs = enrollments_qs.order_by(
        '-academic_year', '-semester', '-enrollment_date', '-id'
    )

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
        'Academic Year',
        'Semester',
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
            e.academic_year,
            e.get_semester_display(),
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
    
    context = {
        'form': form,
        'title': 'Create Enrollment',
        'academic_year_suggestions': _academic_year_suggestions(),
    }
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
    
    context = {
        'form': form,
        'enrollment': enrollment,
        'title': 'Update Enrollment',
        'academic_year_suggestions': _academic_year_suggestions(),
    }
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
@staff_required
def add_grade(request, pk):
    """Add or update grade for an enrollment (administrators only)"""
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
@staff_required
def grade_entry(request):
    """
    Admin-only grade entry hub.

    Student, subject, academic year, semester and score are entered in one
    place. If the student already has the subject in the selected term, that
    record is updated instead of creating a duplicate.
    """
    if request.method == 'POST':
        form = GradeEntryForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            enrollment = Enrollment.objects.filter(
                student=data['student'],
                course=data['course'],
                academic_year=data['academic_year'],
                semester=data['semester'],
            ).first()
            created = enrollment is None
            if created:
                enrollment = Enrollment(
                    student=data['student'],
                    course=data['course'],
                    academic_year=data['academic_year'],
                    semester=data['semester'],
                )

            enrollment.status = data['status']
            enrollment.score = data['score']
            enrollment.attendance_percentage = data.get('attendance_percentage') or 0
            enrollment.notes = data.get('notes') or ''
            enrollment.grade = grade_from_score(data['score']) or None
            enrollment.save()

            student_name = enrollment.student.get_primary_name()
            term = f"{enrollment.get_semester_display()} {enrollment.academic_year}"
            if created:
                messages.success(
                    request,
                    f"Recorded {enrollment.course.code} — {student_name} ({term}).",
                )
            else:
                messages.info(
                    request,
                    f"Updated the existing {enrollment.course.code} record for "
                    f"{student_name} ({term}).",
                )
            return redirect('enrollments:grade_entry')
    else:
        form = GradeEntryForm()

    recent_entries = (
        Enrollment.objects.select_related('student__user', 'course')
        .order_by('-updated_at', '-id')[:8]
    )

    context = {
        'form': form,
        'recent_entries': recent_entries,
        'academic_year_suggestions': _academic_year_suggestions(),
        'default_academic_year': current_academic_year(),
        'default_semester': current_semester(),
    }
    return render(request, 'enrollments/grade_entry.html', context)

def _get_transcript_student(request, student_id):
    from students.models import Student

    student = Student.objects.filter(student_id=student_id).first()
    if not student and str(student_id).isdigit():
        student = Student.objects.filter(pk=int(student_id)).first()
    if not student:
        raise Http404("Student not found")

    user_student = getattr(request.user, 'student', None)
    if not (request.user.is_staff or request.user.is_superuser or user_student == student):
        raise PermissionDenied("You can only view your own transcript.")
    return student


def _build_transcript_context(student):
    summary = summarize_academics(student)
    enrollments = summary['enrollments']

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

    return {
        'student': student,
        'enrollments': enrollments,
        'average_score': summary['avg_score'],
        'total_courses': summary['total_enrolled'],
        'completed_courses': summary['completed_count'],
        'total_credits': summary['total_credits'],
        'earned_credits': summary['earned_credits'],
        'total_credit_points': summary['total_credit_points'],
        'effective_gpa': f"{summary['effective_gpa']:.2f}",
        'standing_en': summary['standing_en'],
        'standing_kh': summary['standing_kh'],
        'standing_badge': summary['standing_badge'],
        'transcript_no': f"BBU-TR-2026-{student.student_id}",
        'issue_date_kh': issue_date_kh,
        'issue_date_en': issue_date_en,
    }


@login_required
def student_transcript(request, student_id):
    """Generate transcript for a student showing all enrollments and grades"""
    student = _get_transcript_student(request, student_id)
    context = _build_transcript_context(student)
    return render(request, 'enrollments/student_transcript.html', context)


def _chrome_executable():
    candidates = [
        os.environ.get('CHROME_PATH'),
        shutil.which('chrome'),
        shutil.which('google-chrome'),
        shutil.which('chromium'),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _localize_asset_urls(html):
    static_dir = settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT
    static_uri = Path(static_dir).resolve().as_uri().rstrip('/')
    media_uri = Path(settings.MEDIA_ROOT).resolve().as_uri().rstrip('/')
    html = html.replace('="/static/', f'="{static_uri}/').replace("='/static/", f"='{static_uri}/")
    html = html.replace('="/media/', f'="{media_uri}/').replace("='/media/", f"='{media_uri}/")
    return html


@login_required
def student_transcript_pdf(request, student_id):
    """Generate an exact A4 PDF of the transcript using headless Chrome."""
    student = _get_transcript_student(request, student_id)
    context = _build_transcript_context(student)
    html = render_to_string('enrollments/student_transcript.html', context, request=request)
    html = _localize_asset_urls(html)

    chrome = _chrome_executable()
    if not chrome:
        return HttpResponse(
            "PDF generation is not available on this server.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )

    with tempfile.TemporaryDirectory(prefix='bbu_transcript_') as temp_dir:
        temp_path = Path(temp_dir)
        html_path = temp_path / 'transcript.html'
        pdf_path = temp_path / 'transcript.pdf'
        html_path.write_text(html, encoding='utf-8')

        command = [
            chrome,
            '--headless=new',
            '--disable-gpu',
            '--no-pdf-header-footer',
            '--allow-file-access-from-files',
            '--virtual-time-budget=5000',
            f'--print-to-pdf={pdf_path}',
            html_path.as_uri(),
        ]
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            subprocess.run(
                command,
                capture_output=True,
                timeout=90,
                check=True,
                creationflags=creationflags,
            )
        except (subprocess.SubprocessError, OSError):
            return HttpResponse(
                "Could not generate the transcript PDF.",
                status=503,
                content_type="text/plain; charset=utf-8",
            )

        if not pdf_path.exists():
            return HttpResponse(
                "Could not generate the transcript PDF.",
                status=503,
                content_type="text/plain; charset=utf-8",
            )
        pdf_bytes = pdf_path.read_bytes()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="transcript_{student.student_id}.pdf"'
    return response

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
