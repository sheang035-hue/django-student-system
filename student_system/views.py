from django.shortcuts import render
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
from students.academics import summarize_academics
from students.models import Student
from courses.models import Course
from enrollments.models import Enrollment

def home(request):
    """
    Home view:
    1. Unauthenticated visitors: Landing page with public stats.
    2. Student users (not staff/admin): Personal Student Portal.
    3. Admin / Staff / Teachers: University Management Dashboard.
    """
    if not request.user.is_authenticated:
        total_students = Student.objects.count()
        total_courses = Course.objects.count()
        total_instructors = Course.objects.filter(instructor__isnull=False).values('instructor').distinct().count()
        avg_gpa_val = Student.objects.filter(gpa__gt=0).aggregate(Avg('gpa'))['gpa__avg']
        avg_gpa = round(avg_gpa_val, 2) if avg_gpa_val else 0.0

        context = {
            'total_students': total_students,
            'total_courses': total_courses,
            'total_instructors': total_instructors,
            'avg_gpa': avg_gpa,
        }
        return render(request, 'landing.html', context)

    # Check if logged-in user is a student (has student profile and is not staff/admin)
    is_staff_or_admin = request.user.is_staff or request.user.is_superuser
    if not is_staff_or_admin and hasattr(request.user, 'student'):
        student = request.user.student
        context = {
            'student': student,
            **summarize_academics(student),
        }
        return render(request, 'students/student_portal.html', context)

    # University Management Dashboard (for Staff, Admins, Instructors)
    total_students = Student.objects.count()
    active_students = Student.objects.filter(is_active=True).count()
    total_courses = Course.objects.count()
    active_courses = Course.objects.filter(status='ACTIVE').count()
    total_enrollments = Enrollment.objects.count()
    total_instructors = Course.objects.filter(instructor__isnull=False).values('instructor').distinct().count()

    # Average GPA calculation
    avg_gpa_val = Student.objects.filter(gpa__gt=0).aggregate(Avg('gpa'))['gpa__avg']
    avg_gpa = round(avg_gpa_val, 2) if avg_gpa_val else 0.0

    # Recently registered students
    recent_students = Student.objects.select_related('user').order_by('-created_at', '-id')[:5]

    # Dean's List — top active students by GPA
    top_students = Student.objects.select_related('user').filter(
        gpa__gt=0, is_active=True
    ).order_by('-gpa', 'student_id')[:5]

    # Recent enrollment activity feed
    recent_enrollments = Enrollment.objects.select_related(
        'student__user', 'course'
    ).order_by('-enrollment_date', '-id')[:5]

    # Needs Attention counters
    ungraded_enrollments = Enrollment.objects.filter(
        status='ENROLLED'
    ).filter(Q(grade__isnull=True) | Q(grade='')).count()
    students_without_enrollment = Student.objects.filter(
        is_active=True, enrollments__isnull=True
    ).count()
    courses_without_enrollment = Course.objects.filter(
        status='ACTIVE', enrollments__isnull=True
    ).count()
    attention_total = ungraded_enrollments + students_without_enrollment + courses_without_enrollment

    # Grade distribution analytics (A, B, C, D, F)
    grade_counts = {
        'A': Enrollment.objects.filter(grade='A').count(),
        'B': Enrollment.objects.filter(grade='B').count(),
        'C': Enrollment.objects.filter(grade='C').count(),
        'D': Enrollment.objects.filter(grade='D').count(),
        'F': Enrollment.objects.filter(grade='F').count(),
    }

    # Top courses by enrollment
    top_courses = Course.objects.annotate(
        enrollment_count=Count('enrollments')
    ).order_by('-enrollment_count')[:5]

    course_labels = [c.code for c in top_courses]
    course_counts = [c.enrollment_count for c in top_courses]

    # Gender ratio and percentages
    male_students = Student.objects.filter(gender='M').count()
    female_students = Student.objects.filter(gender='F').count()
    total_gender = male_students + female_students
    male_pct = round((male_students / total_gender * 100), 1) if total_gender > 0 else 0
    female_pct = round((female_students / total_gender * 100), 1) if total_gender > 0 else 0

    # 30-day KPI trends vs the previous 30-day window
    now = timezone.now()
    last_30 = now - timedelta(days=30)
    prev_30 = now - timedelta(days=60)

    def build_trend(current, previous):
        if previous > 0:
            pct = round((current - previous) / previous * 100, 1)
            return {'has': True, 'pct': abs(pct), 'dir': 'up' if pct >= 0 else 'down'}
        if current > 0:
            return {'has': False, 'pct': None, 'dir': 'up'}
        return {'has': False, 'pct': None, 'dir': 'flat'}

    new_students_30 = Student.objects.filter(created_at__gte=last_30).count()
    prev_students_30 = Student.objects.filter(created_at__gte=prev_30, created_at__lt=last_30).count()
    student_trend = build_trend(new_students_30, prev_students_30)

    new_courses_30 = Course.objects.filter(created_at__gte=last_30).count()
    prev_courses_30 = Course.objects.filter(created_at__gte=prev_30, created_at__lt=last_30).count()
    course_trend = build_trend(new_courses_30, prev_courses_30)

    new_enroll_30 = Enrollment.objects.filter(enrollment_date__gte=last_30.date()).count()
    prev_enroll_30 = Enrollment.objects.filter(
        enrollment_date__gte=prev_30.date(), enrollment_date__lt=last_30.date()
    ).count()
    enrollment_trend = build_trend(new_enroll_30, prev_enroll_30)

    recent_score = Enrollment.objects.filter(
        status='COMPLETED', completed_date__gte=last_30.date()
    ).aggregate(Avg('score'))['score__avg']
    previous_score = Enrollment.objects.filter(
        status='COMPLETED', completed_date__gte=prev_30.date(), completed_date__lt=last_30.date()
    ).aggregate(Avg('score'))['score__avg']
    gpa_trend = build_trend(float(recent_score or 0), float(previous_score or 0))

    context = {
        'total_students': total_students,
        'active_students': active_students,
        'total_courses': total_courses,
        'active_courses': active_courses,
        'total_enrollments': total_enrollments,
        'total_instructors': total_instructors,
        'academic_years': 4,
        'avg_gpa': avg_gpa,
        'recent_students': recent_students,
        'top_students': top_students,
        'recent_enrollments': recent_enrollments,
        'ungraded_enrollments': ungraded_enrollments,
        'students_without_enrollment': students_without_enrollment,
        'courses_without_enrollment': courses_without_enrollment,
        'attention_total': attention_total,
        'grade_a': grade_counts['A'],
        'grade_b': grade_counts['B'],
        'grade_c': grade_counts['C'],
        'grade_d': grade_counts['D'],
        'grade_f': grade_counts['F'],
        'course_labels': course_labels,
        'course_counts': course_counts,
        'male_students': male_students,
        'female_students': female_students,
        'male_pct': male_pct,
        'female_pct': female_pct,
        'student_trend': student_trend,
        'course_trend': course_trend,
        'enrollment_trend': enrollment_trend,
        'gpa_trend': gpa_trend,
    }

    return render(request, 'home.html', context)
