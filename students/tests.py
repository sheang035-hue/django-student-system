from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from students.models import Student
from datetime import date

class StudentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='johndoe',
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            password='testpassword123'
        )
        self.student = Student.objects.create(
            user=self.user,
            student_id='STU101',
            date_of_birth=date(2001, 5, 20),
            gender='M',
            phone_number='012345678',
            address='Street 271',
            city='Phnom Penh',
            country='Cambodia'
        )

    def test_student_str(self):
        self.assertEqual(str(self.student), 'STU101 - John Doe')

    def test_student_str_with_khmer_name_as_primary(self):
        self.student.khmer_name = 'សុខ តារា'
        self.student.save()
        self.assertEqual(str(self.student), 'STU101 - សុខ តារា')
        self.assertEqual(self.student.get_primary_name(), 'សុខ តារា')

    def test_student_absolute_url(self):
        self.assertEqual(
            self.student.get_absolute_url(),
            reverse('students:student_detail', kwargs={'pk': self.student.pk})
        )


class StudentViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='teacher',
            password='password123'
        )
        self.student = Student.objects.create(
            user=self.user,
            student_id='STU202',
            date_of_birth=date(2002, 1, 1),
            gender='F',
            address='Street 10',
            city='Siem Reap',
            country='Cambodia'
        )

    def test_student_list_login_required(self):
        response = self.client.get(reverse('students:student_list'))
        self.assertEqual(response.status_code, 302)

    def test_student_list_authenticated(self):
        self.client.login(username='teacher', password='password123')
        self.student.khmer_name = 'ជា ពិសិដ្ឋ'
        self.student.save()
        response = self.client.get(reverse('students:student_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'STU202')
        self.assertContains(response, 'ជា ពិសិដ្ឋ')
        # Check avatar and two name columns presence
        self.assertContains(response, 'Photo')
        self.assertContains(response, 'Khmer Name')
        self.assertContains(response, 'English Name')

    def test_student_list_search_by_khmer_name(self):
        self.client.login(username='teacher', password='password123')
        self.student.khmer_name = 'ហេង មុនី'
        self.student.save()
        response = self.client.get(reverse('students:student_list') + '?q=មុនី')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ហេង មុនី')
        self.assertContains(response, 'STU202')

    def test_student_register_page(self):
        response = self.client.get(reverse('students:register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Khmer Name')
        self.assertContains(response, 'Profile Picture')

    def test_student_register_post_with_photo(self):
        tiny_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00'
            b'\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00'
            b'\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02'
            b'\x44\x01\x00\x3b'
        )
        photo = SimpleUploadedFile('avatar.gif', tiny_gif, content_type='image/gif')
        data = {
            'username': 'newstudent',
            'first_name': 'Dara',
            'last_name': 'Sok',
            'email': 'dara@example.com',
            'password1': 'SecretPass123!',
            'password2': 'SecretPass123!',
            'student_id': 'STU888',
            'khmer_name': 'សុខ តារា',
            'date_of_birth': '2003-05-10',
            'gender': 'M',
            'phone_number': '012345678',
            'address': 'Street 2004',
            'city': 'Phnom Penh',
            'country': 'Cambodia',
            'profile_picture': photo,
        }
        response = self.client.post(reverse('students:register'), data, follow=True)
        self.assertEqual(response.status_code, 200)
        new_student = Student.objects.filter(student_id='STU888').first()
        self.assertIsNotNone(new_student)
        self.assertEqual(new_student.khmer_name, 'សុខ តារា')
        self.assertTrue(bool(new_student.profile_picture))
        if new_student.profile_picture:
            new_student.profile_picture.delete(save=False)

    def test_student_detail_view(self):
        self.client.login(username='teacher', password='password123')
        self.student.khmer_name = 'កែវ សម្បត្តិ'
        self.student.save()
        response = self.client.get(reverse('students:student_detail', kwargs={'pk': self.student.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'STU202')
        self.assertContains(response, 'កែវ សម្បត្តិ')
        self.assertContains(response, '<strong>English Name:</strong>')
        self.assertContains(response, '<strong>Enrollment Date:</strong>')
        # Ensure no raw unparsed template tags are rendered in HTML
        self.assertNotContains(response, '{{')

    def test_student_cbv_create_and_update(self):
        self.client.login(username='teacher', password='password123')
        # Test CBV create
        response = self.client.post(reverse('students:student_create_cbv'), {
            'student_id': 'STU999',
            'khmer_name': 'សុខ វិបុល',
            'date_of_birth': '2002-04-15',
            'gender': 'M',
            'phone_number': '012999888',
            'address': 'St 123',
            'city': 'Phnom Penh',
            'country': 'Cambodia',
        })
        self.assertEqual(response.status_code, 302)
        created = Student.objects.filter(student_id='STU999').first()
        self.assertIsNotNone(created)
        self.assertEqual(created.khmer_name, 'សុខ វិបុល')

        # Test CBV update
        response_update = self.client.post(reverse('students:student_update_cbv', kwargs={'pk': created.pk}), {
            'student_id': 'STU999',
            'khmer_name': 'សុខ វិបុល រតនៈ',
            'date_of_birth': '2002-04-15',
            'gender': 'M',
            'phone_number': '012999888',
            'address': 'St 123',
            'city': 'Phnom Penh',
            'country': 'Cambodia',
        })
        self.assertEqual(response_update.status_code, 302)
        created.refresh_from_db()
        self.assertEqual(created.khmer_name, 'សុខ វិបុល រតនៈ')


class RootEndpointsTest(TestCase):
    def test_favicon_redirect(self):
        response = self.client.get('/favicon.ico')
        self.assertEqual(response.status_code, 301)
        self.assertIn('favicon.ico', response.get('Location'))

    def test_chrome_devtools_probe(self):
        response = self.client.get('/.well-known/appspecific/com.chrome.devtools.json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})


class RoleBasedDashboardTest(TestCase):
    """Test role-based dashboard rendering: Students vs Admin/Staff vs Public"""

    def setUp(self):
        from courses.models import Course
        from enrollments.models import Enrollment

        self.client = Client()
        # Admin / Staff user
        self.admin = User.objects.create_superuser(
            username='admin_staff',
            password='password123',
            email='admin@bbu.edu.kh'
        )
        # Student user
        self.student_user = User.objects.create_user(
            username='song_heang1',
            first_name='Song',
            last_name='Heang',
            password='password123'
        )
        self.student = Student.objects.create(
            user=self.student_user,
            student_id='STU0001',
            khmer_name='សុង ហៀង',
            date_of_birth=date(2002, 5, 10),
            gender='M',
            address='Phnom Penh',
            city='Phnom Penh',
            country='Cambodia',
            gpa=3.60
        )
        self.course = Course.objects.create(
            code='CS101',
            title='Intro to Computer Science',
            description='Fundamentals',
            credits=3,
            level='100',
            capacity=30,
            status='ACTIVE',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 1),
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='COMPLETED',
            score=90.0,
            grade='A'
        )

    def test_unauthenticated_visitor_gets_landing_page(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html')

    def test_student_gets_personal_student_portal(self):
        self.client.login(username='song_heang1', password='password123')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'students/student_portal.html')
        self.assertContains(response, 'សុង ហៀង')
        self.assertContains(response, 'STU0001')
        self.assertContains(response, 'CS101')
        self.assertContains(response, 'My Official Transcript')
        # Ensure student does NOT see management "+ Add Student" button
        self.assertNotContains(response, '➕ Add Student')

    def test_admin_gets_university_management_dashboard(self):
        self.client.login(username='admin_staff', password='password123')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        self.assertContains(response, '➕ Add Student')
        self.assertContains(response, '📋 Enroll Course')
        self.assertContains(response, 'Academic Dashboard')



