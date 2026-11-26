from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from students.models import Student
from students.academics import summarize_academics
from courses.models import Course
from enrollments.models import Enrollment
from datetime import date

class EnrollmentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student1', password='password123')
        self.student = Student.objects.create(
            user=self.user,
            student_id='STU301',
            date_of_birth=date(2000, 3, 10),
            gender='M',
            address='Street 1',
            city='Phnom Penh',
            country='Cambodia'
        )
        self.course = Course.objects.create(
            code='CS401',
            title='Software Engineering',
            description='Software engineering principles',
            credits=3,
            level='400',
            capacity=30,
            status='ACTIVE',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )

    def test_grade_calculation(self):
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            score=92.5
        )
        self.assertEqual(enrollment.grade, 'A')

    def test_enrollment_str(self):
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            score=75
        )
        self.assertEqual(str(enrollment), 'STU301 - CS401')


class EnrollmentViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username='admin_user', password='password123', email='admin@test.com')
        self.user = User.objects.create_user(username='student2', password='password123')
        self.student = Student.objects.create(
            user=self.user,
            student_id='STU302',
            date_of_birth=date(2000, 3, 10),
            gender='F',
            address='Street 2',
            city='Battambang',
            country='Cambodia'
        )
        self.course = Course.objects.create(
            code='CS402',
            title='Database Systems',
            description='SQL and NoSQL',
            credits=3,
            level='400',
            capacity=30,
            status='ACTIVE',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            score=88.0,
            status='COMPLETED'
        )

    def test_enrollment_list_requires_login(self):
        response = self.client.get(reverse('enrollments:enrollment_list'))
        self.assertEqual(response.status_code, 302)

    def test_enrollment_list_authenticated(self):
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('enrollments:enrollment_list'))
        self.assertEqual(response.status_code, 200)

    def test_student_transcript_view(self):
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('enrollments:student_transcript', kwargs={'student_id': self.student.student_id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CS402')

    def test_add_grade_forbidden_for_non_staff(self):
        self.client.login(username='student2', password='password123')
        response = self.client.get(reverse('enrollments:add_grade', kwargs={'pk': self.enrollment.pk}))
        self.assertEqual(response.status_code, 403)

    def test_add_grade_allowed_for_staff(self):
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('enrollments:add_grade', kwargs={'pk': self.enrollment.pk}))
        self.assertEqual(response.status_code, 200)

    def test_enrollment_create_view_searchable_dropdown(self):
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('enrollments:enrollment_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tom-select.bootstrap5.min.css')
        self.assertContains(response, 'tom-select.complete.min.js')
        self.assertContains(response, 'id_student')
        self.assertContains(response, 'id_course')

        # Test creating a new enrollment
        new_course = Course.objects.create(
            code='CS403', title='Cloud Computing', description='AWS/GCP',
            credits=3, level='400', capacity=30, status='ACTIVE',
            start_date=date(2024, 1, 1), end_date=date(2024, 6, 1)
        )
        post_response = self.client.post(reverse('enrollments:enrollment_create'), {
            'student': self.student.pk,
            'course': new_course.pk,
            'academic_year': '2026-2027',
            'semester': 'S1',
            'status': 'ENROLLED',
        })
        self.assertEqual(post_response.status_code, 302)
        self.assertTrue(Enrollment.objects.filter(student=self.student, course=new_course).exists())

    def test_same_subject_can_be_repeated_in_another_semester(self):
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            academic_year='2025-2026',
            semester='S1',
            status='COMPLETED',
            score=51.0,
        )
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            academic_year='2025-2026',
            semester='S2',
            status='COMPLETED',
            score=78.0,
        )
        self.assertEqual(
            Enrollment.objects.filter(student=self.student, course=self.course).count(),
            3,
        )

    def test_latest_attempt_counts_for_gpa_and_credits(self):
        # Move the original attempt into an older term so it is superseded.
        self.enrollment.academic_year = '2025-2026'
        self.enrollment.semester = 'S1'
        self.enrollment.save(update_fields=['academic_year', 'semester'])

        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            academic_year='2025-2026',
            semester='S2',
            status='COMPLETED',
            score=51.0,
        )
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            academic_year='2026-2027',
            semester='S1',
            status='COMPLETED',
            score=78.0,
        )

        summary = summarize_academics(self.student)

        # The three attempts are visible, but the course only counts once.
        self.assertEqual(summary['total_enrolled'], 1)
        self.assertEqual(summary['completed_count'], 1)
        self.assertEqual(summary['total_credits'], 3)
        self.assertEqual(summary['earned_credits'], 3)
        # Latest attempt (78 -> B, 3.00) replaces the earlier attempts in GPA.
        self.assertEqual(summary['calculated_gpa'], 3.0)

        attempts = sorted(summary['enrollments'], key=lambda e: e.attempt_number)
        self.assertEqual([e.attempt_number for e in attempts], [1, 2, 3])
        self.assertTrue(attempts[0].is_superseded)
        self.assertTrue(attempts[1].is_superseded)
        self.assertFalse(attempts[2].is_superseded)
        self.assertTrue(attempts[2].counts_toward_gpa)

    def test_grade_entry_forbidden_for_non_staff(self):
        self.client.login(username='student2', password='password123')
        response = self.client.get(reverse('enrollments:grade_entry'))
        self.assertEqual(response.status_code, 403)

    def test_grade_entry_creates_then_updates_same_term(self):
        course = Course.objects.create(
            code='CS404', title='Mobile Development', description='Android',
            credits=3, level='400', capacity=30, status='ACTIVE',
            start_date=date(2024, 1, 1), end_date=date(2024, 6, 1),
        )
        self.client.login(username='admin_user', password='password123')
        payload = {
            'student': self.student.pk,
            'course': course.pk,
            'academic_year': '2025-2026',
            'semester': 'S2',
            'status': 'COMPLETED',
            'score': '88',
            'attendance_percentage': '90',
            'notes': 'Recorded from the grade entry page',
        }
        response = self.client.post(reverse('enrollments:grade_entry'), payload)
        self.assertEqual(response.status_code, 302)
        record = Enrollment.objects.get(student=self.student, course=course)
        self.assertEqual(record.grade, 'A')
        self.assertEqual(float(record.score), 88.0)

        payload['score'] = '50'
        payload['attendance_percentage'] = ''
        response = self.client.post(reverse('enrollments:grade_entry'), payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Enrollment.objects.filter(student=self.student, course=course).count(), 1
        )
        record.refresh_from_db()
        self.assertEqual(record.grade, 'C')
        self.assertEqual(float(record.score), 50.0)
