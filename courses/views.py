import csv
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from student_system.permissions import StaffRequiredMixin, staff_required
from .models import Course
from .forms import CourseForm, CourseFilterForm

# Order used when rendering semesters inside a study year.
SEMESTER_ORDER = ['S1', 'S2', 'SUM']


def _safe_next(request, fallback):
    """Return a validated ``next`` URL from the request, or the fallback."""
    target = request.POST.get('next') or request.GET.get('next')
    if target and url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return target
    return fallback


def _student_enrollment_map(student):
    """Map ``course_id`` to the most relevant enrollment for a student.

    A completed attempt wins over an in-progress attempt so the curriculum
    shows the best outcome for a repeated subject.
    """
    if not student:
        return {}

    latest = {}
    for enrollment in student.enrollments.select_related('course').all():
        current = latest.get(enrollment.course_id)
        if current is None:
            latest[enrollment.course_id] = enrollment
        elif enrollment.status == 'COMPLETED' and current.status != 'COMPLETED':
            latest[enrollment.course_id] = enrollment
    return latest


def _build_curriculum(courses):
    """Group courses into ``Year -> Semester -> subjects`` buckets."""
    year_map = {}
    unscheduled = []

    for course in courses:
        if not course.semester:
            unscheduled.append(course)
            continue

        year = course.study_year
        year_bucket = year_map.setdefault(year, {
            'year': year,
            'label': course.study_year_label,
            'level_code': str(year * 100),
            'semesters': {},
        })
        semester_bucket = year_bucket['semesters'].setdefault(course.semester, {
            'code': course.semester,
            'label': course.get_semester_display(),
            'courses': [],
            'credits': 0,
        })
        semester_bucket['courses'].append(course)
        semester_bucket['credits'] += course.credits or 0

    curriculum = []
    for year in sorted(year_map):
        year_bucket = year_map[year]
        semesters = [
            year_bucket['semesters'][code]
            for code in SEMESTER_ORDER
            if code in year_bucket['semesters']
        ]
        for semester in semesters:
            semester['courses'].sort(key=lambda c: c.code)
            semester['count'] = len(semester['courses'])
        year_bucket['semesters'] = semesters
        year_bucket['total_courses'] = sum(s['count'] for s in semesters)
        year_bucket['total_credits'] = sum(s['credits'] for s in semesters)
        curriculum.append(year_bucket)

    unscheduled.sort(key=lambda c: c.code)
    return curriculum, unscheduled


def _semester_context(request, manage_mode=False):
    """Build the shared context for the read-only and admin semester views."""
    is_staff = request.user.is_staff or request.user.is_superuser
    student = None if is_staff else getattr(request.user, 'student', None)

    courses_qs = Course.objects.select_related('instructor').all()

    year_filter = request.GET.get('year', '').strip()
    semester_filter = request.GET.get('semester', '').strip()
    search = request.GET.get('search', '').strip()

    if year_filter in Course.LEVEL_TO_YEAR:
        courses_qs = courses_qs.filter(level=year_filter)
    if semester_filter in dict(Course.SEMESTER_CHOICES):
        courses_qs = courses_qs.filter(semester=semester_filter)
    if search:
        courses_qs = courses_qs.filter(
            Q(code__icontains=search) | Q(title__icontains=search)
        )

    courses_qs = courses_qs.order_by('level', 'semester', 'code')
    enrollment_map = _student_enrollment_map(student)
    curriculum, unscheduled = _build_curriculum(courses_qs)

    for year_bucket in curriculum:
        for semester in year_bucket['semesters']:
            for course in semester['courses']:
                course.student_enrollment = enrollment_map.get(course.pk)
    for course in unscheduled:
        course.student_enrollment = enrollment_map.get(course.pk)

    scheduled_count = sum(
        semester['count']
        for year_bucket in curriculum
        for semester in year_bucket['semesters']
    )

    return {
        'curriculum': curriculum,
        'unscheduled_courses': unscheduled,
        'scheduled_count': scheduled_count,
        'total_subjects': scheduled_count + len(unscheduled),
        'total_credits': sum(
            course.credits or 0
            for year_bucket in curriculum
            for semester in year_bucket['semesters']
            for course in semester['courses']
        ) + sum(course.credits or 0 for course in unscheduled),
        'semester_choices': Course.SEMESTER_CHOICES,
        'level_choices': Course.LEVEL_CHOICES,
        'selected_year': year_filter,
        'selected_semester': semester_filter,
        'search_query': search,
        'student_view': bool(student),
        'manage_mode': manage_mode,
        'is_staff_view': is_staff,
    }


def semester_overview(request):
    """Read-only curriculum grouped by study year and semester."""
    context = _semester_context(request, manage_mode=False)
    context.update({
        'page_title': 'Subjects by Semester / មុខវិជ្ជាតាមឆមាស',
        'page_subtitle': (
            'Browse every subject in the university curriculum, organised by '
            'study year and semester.'
        ),
    })
    return render(request, 'courses/semester_subjects.html', context)


@login_required
@staff_required
def semester_manage(request):
    """Administrator view for adding and changing the subjects of each semester."""
    context = _semester_context(request, manage_mode=True)
    context.update({
        'page_title': 'Manage Semester Subjects / គ្រប់គ្រងមុខវិជ្ជាតាមឆមាស',
        'page_subtitle': (
            'Add a subject to a semester, move it to another semester, or edit '
            'its details. Changes are visible to students immediately.'
        ),
    })
    return render(request, 'courses/semester_subjects.html', context)


# Function-Based Views (FBV)

def course_list(request):
    """List all courses with filtering options, KPI stats, and pagination"""
    courses_qs = Course.objects.select_related('instructor').all()
    form = CourseFilterForm(request.GET or None)
    
    # Check both form cleaned_data and direct GET parameters for search/status
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '').strip()
    level = request.GET.get('level', '').strip()
    semester = request.GET.get('semester', '').strip()
    
    if search:
        courses_qs = courses_qs.filter(
            Q(code__icontains=search) |
            Q(title__icontains=search)
        )
    if status:
        courses_qs = courses_qs.filter(status=status)
    if level:
        courses_qs = courses_qs.filter(level=level)
    if semester:
        courses_qs = courses_qs.filter(semester=semester)

    courses_qs = courses_qs.order_by('code')
    total_count = Course.objects.count()
    active_count = Course.objects.filter(status='ACTIVE').count()
    
    paginator = Paginator(courses_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'courses': page_obj,
        'page_obj': page_obj,
        'form': form,
        'total_count': total_count,
        'active_count': active_count,
        'semester_choices': Course.SEMESTER_CHOICES,
        'selected_semester': semester,
    }
    return render(request, 'courses/course_list.html', context)


@login_required
@staff_required
def export_courses_csv(request):
    """Export filtered or all academic courses to CSV spreadsheet with UTF-8 BOM."""
    courses_qs = Course.objects.select_related('instructor').all()
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '').strip()
    level = request.GET.get('level', '').strip()
    semester = request.GET.get('semester', '').strip()
    
    if search:
        courses_qs = courses_qs.filter(
            Q(code__icontains=search) |
            Q(title__icontains=search)
        )
    if status:
        courses_qs = courses_qs.filter(status=status)
    if level:
        courses_qs = courses_qs.filter(level=level)
    if semester:
        courses_qs = courses_qs.filter(semester=semester)
        
    courses_qs = courses_qs.order_by('code')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="bbu_academic_courses.csv"'
    
    # Write UTF-8 BOM for Microsoft Excel
    response.write('\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    writer.writerow([
        'Course Code',
        'Course Title',
        'Instructor',
        'Credits',
        'Level',
        'Semester',
        'Capacity',
        'Status',
        'Start Date',
        'End Date'
    ])
    
    for c in courses_qs:
        instructor_name = c.instructor.get_full_name() if c.instructor else 'Unassigned'
        writer.writerow([
            c.code,
            c.title,
            instructor_name,
            c.credits,
            c.get_level_display(),
            c.semester_label,
            c.capacity,
            c.get_status_display(),
            c.start_date.strftime('%Y-%m-%d') if c.start_date else '',
            c.end_date.strftime('%Y-%m-%d') if c.end_date else ''
        ])
    return response

def course_detail(request, pk):
    """Display detailed information about a course"""
    # Get the course by primary key
    course = get_object_or_404(Course, pk=pk)
    # Get all enrollments for the course
    enrollments = course.enrollments.all()
    # Get the total number of students
    total_students = enrollments.count()
    # Context for the template
    context = {
        'course': course,
        'enrollments': enrollments,
        'total_students': total_students,
    }
    # Render the template
    return render(request, 'courses/course_detail.html', context)

#@login_required is a decorator that requires login to access a view
@login_required
@staff_required
# Course Creation View
def course_create(request):
    """Create a new course"""
    next_url = request.POST.get('next') or request.GET.get('next', '')
    # Check if the request method is POST
    if request.method == 'POST':
        # Create a new form with the POST data
        form = CourseForm(request.POST)
        # Check if the form is valid
        if form.is_valid():
            # Save the form
            course = form.save()
            messages.success(request, f"Course {course.code} saved successfully.")
            # Return to the semester manager when the form was opened there.
            return redirect(_safe_next(request, course.get_absolute_url()))
    else:
        # Pre-select the year/semester when coming from the semester manager.
        initial = {}
        semester = request.GET.get('semester', '').strip()
        level = request.GET.get('level', '').strip()
        if semester in dict(Course.SEMESTER_CHOICES):
            initial['semester'] = semester
        if level in dict(Course.LEVEL_CHOICES):
            initial['level'] = level
        # Create a new form
        form = CourseForm(initial=initial)
    # Context for the template
    context = {'form': form, 'title': 'Create Course', 'next_url': next_url}
    # Render the template
    return render(request, 'courses/course_form.html', context)

@login_required
@staff_required
# Course Update View
def course_update(request, pk):
    """Update course information"""
    # Get the course by primary key
    course = get_object_or_404(Course, pk=pk)
    next_url = request.POST.get('next') or request.GET.get('next', '')
    # Check if the request method is POST
    if request.method == 'POST':
        # Create a new form with the POST data
        form = CourseForm(request.POST, instance=course)
        # Check if the form is valid
        if form.is_valid():
            # Save the form
            form.save()
            messages.success(request, f"Course {course.code} updated successfully.")
            # Return to the semester manager when the form was opened there.
            return redirect(_safe_next(request, course.get_absolute_url()))
    else:
        # Create a new form with the instance
        form = CourseForm(instance=course)
    # Context for the template
    context = {
        'form': form,
        'course': course,
        'title': 'Update Course',
        'next_url': next_url,
    }
    # Render the template
    return render(request, 'courses/course_form.html', context)

@login_required
@staff_required
# Course Deletion View
def course_delete(request, pk):
    """Delete a course"""
    # Get the course by primary key
    course = get_object_or_404(Course, pk=pk)
    # Check if the request method is POST
    if request.method == 'POST':
        code = course.code
        # Delete the course
        course.delete()
        messages.success(request, f"Course {code} deleted successfully.")
        # Return to the semester manager when the deletion started there.
        return redirect(_safe_next(request, reverse('courses:course_list')))
    # Context for the template
    context = {'course': course}
    # Render the template
    return render(request, 'courses/course_confirm_delete.html', context)

# Class-Based Views (CBV)
# CBV is a view that is defined as a class
# CBV is more concise and easier to understand than FBV
# CBV is more flexible than FBV
# CBV is more reusable than FBV
# CBV is more maintainable than FBV

# Class-Based View for listing courses with pagination
# ListView is a generic view that is used to display a list of objects
class CourseListView(ListView):
    """Class-based view for listing courses with pagination"""
    # Specify the model to use for the view
    model = Course
    # Specify the template to use for the view
    template_name = 'courses/course_list.html'
    # Specify the context object name to use for the view
    context_object_name = 'courses'
    # Specify the pagination to use for the view
    paginate_by = 10
    
    # get_queryset method is used to get the queryset for the view
    # it is used to get the queryset for the view
    def get_queryset(self):
        queryset = Course.objects.annotate(student_count=Count('enrollments'))
        
        level = self.request.GET.get('level')
        status = self.request.GET.get('status')
        search = self.request.GET.get('search')
        
        if level:
            queryset = queryset.filter(level=level)
        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(title__icontains=search)
            )
        
        return queryset.order_by('code')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CourseFilterForm(self.request.GET or None)
        return context

class CourseDetailView(DetailView):
    """Class-based view for course details"""
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['enrollments'] = self.object.enrollments.all()
        context['total_students'] = self.object.enrollments.count()
        return context

class CourseCreateView(StaffRequiredMixin, CreateView):
    """Class-based view for creating a new course"""
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('courses:course_list')

class CourseUpdateView(StaffRequiredMixin, UpdateView):
    """Class-based view for updating course information"""
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('courses:course_list')

class CourseDeleteView(StaffRequiredMixin, DeleteView):
    """Class-based view for deleting a course"""
    model = Course
    template_name = 'courses/course_confirm_delete.html'
    success_url = reverse_lazy('courses:course_list')
