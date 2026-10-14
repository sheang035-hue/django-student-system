from django.shortcuts import render
from django.db.models import Avg, Count
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

        total_credit_points = 0.0
        total_credits = 0
        earned_credits = 0
        completed_courses = []
        in_progress_courses = []

        for e in enrollments:
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
            total_credits += credits

            if e.status == 'COMPLETED':
                cp = round(credits * gp, 2)
                e.credit_points = cp
                total_credit_points += cp
                earned_credits += credits
                e.is_passed = grade != 'F' and (e.score is None or e.score >= 50)
                completed_courses.append(e)
            else:
                e.credit_points = 0.0
                e.is_passed = False
                in_progress_courses.append(e)

            raw_title = e.course.title if e.course else ''
            if '(' in raw_title and ')' in raw_title:
                en_title = raw_title[:raw_title.find('(')].strip()
                kh_title = raw_title[raw_title.find('(')+1:raw_title.rfind(')')].strip()
            else:
                en_title = raw_title
                kh_title = course_khmer_map.get(e.course.code, '') if e.course else ''
            e.clean_en_title = en_title
            e.clean_kh_title = kh_title

        avg_score_val = sum(float(e.score) for e in completed_courses if e.score is not None) / len(completed_courses) if completed_courses else 0.0
        avg_score = round(avg_score_val, 1)

        calculated_gpa = round(total_credit_points / earned_credits, 2) if earned_credits > 0 else 0.0
        effective_gpa = float(student.gpa) if float(student.gpa) > 0 else calculated_gpa

        # Academic Standing classification
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
            standing_kh = "ត្រូវតាមដានការសិក្សា"
            standing_badge = "danger"

        # Grade counts
        grade_a_count = sum(1 for e in enrollments if e.grade == 'A')
        grade_b_count = sum(1 for e in enrollments if e.grade in ['B', 'B+'])
        grade_c_count = sum(1 for e in enrollments if e.grade in ['C', 'C+'])
        grade_d_count = sum(1 for e in enrollments if e.grade == 'D')
        grade_f_count = sum(1 for e in enrollments if e.grade == 'F')

        context = {
            'student': student,
            'enrollments': enrollments,
            'total_enrolled': len(enrollments),
            'completed_count': len(completed_courses),
            'in_progress_count': len(in_progress_courses),
            'total_credits': total_credits,
            'earned_credits': earned_credits,
            'effective_gpa': effective_gpa,
            'avg_score': avg_score,
            'standing_en': standing_en,
            'standing_kh': standing_kh,
            'standing_badge': standing_badge,
            'grade_a_count': grade_a_count,
            'grade_b_count': grade_b_count,
            'grade_c_count': grade_c_count,
            'grade_d_count': grade_d_count,
            'grade_f_count': grade_f_count,
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
    }

    return render(request, 'home.html', context)
