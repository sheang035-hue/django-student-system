import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.urls import reverse_lazy
from .models import Course
from .forms import CourseForm, CourseFilterForm

# Function-Based Views (FBV)

def course_list(request):
    """List all courses with filtering options, KPI stats, and pagination"""
    courses_qs = Course.objects.select_related('instructor').all()
    form = CourseFilterForm(request.GET or None)
    
    # Check both form cleaned_data and direct GET parameters for search/status
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '').strip()
    level = request.GET.get('level', '').strip()
    
    if search:
        courses_qs = courses_qs.filter(
            Q(code__icontains=search) |
            Q(title__icontains=search)
        )
    if status:
        courses_qs = courses_qs.filter(status=status)
    if level:
        courses_qs = courses_qs.filter(level=level)

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
    }
    return render(request, 'courses/course_list.html', context)


@login_required
def export_courses_csv(request):
    """Export filtered or all academic courses to CSV spreadsheet with UTF-8 BOM."""
    courses_qs = Course.objects.select_related('instructor').all()
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '').strip()
    level = request.GET.get('level', '').strip()
    
    if search:
        courses_qs = courses_qs.filter(
            Q(code__icontains=search) |
            Q(title__icontains=search)
        )
    if status:
        courses_qs = courses_qs.filter(status=status)
    if level:
        courses_qs = courses_qs.filter(level=level)
        
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
# Course Creation View
def course_create(request):
    """Create a new course"""
    # Check if the request method is POST
    if request.method == 'POST':
        # Create a new form with the POST data
        form = CourseForm(request.POST)
        # Check if the form is valid
        if form.is_valid():
            # Save the form
            form.save()
            # Redirect to the course list
            return redirect('courses:course_list')
    else:
        # Create a new form
        form = CourseForm()
    # Context for the template
    context = {'form': form, 'title': 'Create Course'}
    # Render the template
    return render(request, 'courses/course_form.html', context)

@login_required
# Course Update View
def course_update(request, pk):
    """Update course information"""
    # Get the course by primary key
    course = get_object_or_404(Course, pk=pk)
    # Check if the request method is POST
    if request.method == 'POST':
        # Create a new form with the POST data
        form = CourseForm(request.POST, instance=course)
        # Check if the form is valid
        if form.is_valid():
            # Save the form
            form.save()
            # Redirect to the course detail
            return redirect('courses:course_detail', pk=course.pk)
    else:
        # Create a new form with the instance
        form = CourseForm(instance=course)
    # Context for the template
    context = {'form': form, 'course': course, 'title': 'Update Course'}
    # Render the template
    return render(request, 'courses/course_form.html', context)

@login_required
# Course Deletion View
def course_delete(request, pk):
    """Delete a course"""
    # Get the course by primary key
    course = get_object_or_404(Course, pk=pk)
    # Check if the request method is POST
    if request.method == 'POST':
        # Delete the course
        course.delete()
        # Redirect to the course list
        return redirect('courses:course_list')
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

class CourseCreateView(LoginRequiredMixin, CreateView):
    """Class-based view for creating a new course"""
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('courses:course_list')

class CourseUpdateView(LoginRequiredMixin, UpdateView):
    """Class-based view for updating course information"""
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('courses:course_list')

class CourseDeleteView(LoginRequiredMixin, DeleteView):
    """Class-based view for deleting a course"""
    model = Course
    template_name = 'courses/course_confirm_delete.html'
    success_url = reverse_lazy('courses:course_list')
