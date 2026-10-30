from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from backend.models import Category, Course, Enrollment, ContactMessage

class AdminDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create an admin user
        self.admin_user = User.objects.create_superuser(
            username='adminuser',
            email='admin@zylora.com',
            password='adminpassword123',
            first_name='Admin',
            last_name='User'
        )
        # Create a regular student user
        self.student = User.objects.create_user(
            username='normalstudent',
            email='student@test.com',
            password='studentpass123',
            first_name='Normal',
            last_name='Student'
        )
        # Create Category and Course
        self.category = Category.objects.create(name='Computer Science', icon='fa-code')
        self.course = Course.objects.create(
            title='Intro to Python',
            category=self.category,
            instructor_name='Dr. Smith',
            price=49.99,
            duration_weeks=4,
            description='A beginner course on Python.'
        )

    def test_admin_login_page_renders(self):
        response = self.client.get(reverse('backend:admin_login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Management Portal')

    def test_admin_login_success(self):
        response = self.client.post(reverse('backend:admin_login'), {
            'username': 'adminuser',
            'password': 'adminpassword123',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Platform Overview')

    def test_admin_login_denies_non_staff(self):
        response = self.client.post(reverse('backend:admin_login'), {
            'username': 'normalstudent',
            'password': 'studentpass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Access denied')

    def test_dashboard_requires_staff(self):
        response = self.client.get(reverse('backend:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('backend:admin_login'), response.url)

    def test_dashboard_renders_for_staff(self):
        self.client.login(username='adminuser', password='adminpassword123')
        response = self.client.get(reverse('backend:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Platform Overview')
        self.assertContains(response, 'Students')

    def test_students_list(self):
        self.client.login(username='adminuser', password='adminpassword123')
        response = self.client.get(reverse('backend:students_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'normalstudent')

    def test_student_toggle_active_status(self):
        self.client.login(username='adminuser', password='adminpassword123')
        self.assertTrue(self.student.is_active)
        response = self.client.get(reverse('backend:student_toggle_status', args=[self.student.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)

    def test_courses_list_and_create(self):
        self.client.login(username='adminuser', password='adminpassword123')
        response = self.client.get(reverse('backend:courses_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Intro to Python')

        # Test Course Creation
        post_data = {
            'title': 'Advanced Django Web Development',
            'category': self.category.id,
            'instructor_name': 'Sarah Connor',
            'price': 129.00,
            'duration_weeks': 8,
            'level': 'Advanced',
            'description': 'Master Django ORM, query optimizations, and caching.',
            'is_published': True,
        }
        res = self.client.post(reverse('backend:course_create'), post_data, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Course.objects.filter(title='Advanced Django Web Development').exists())

    def test_course_lessons_crud(self):
        from backend.models import Lesson
        self.client.login(username='adminuser', password='adminpassword123')
        
        # View lessons for course
        response = self.client.get(reverse('backend:course_lessons', args=[self.course.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Intro to Python')

        # Create Lesson
        lesson_data = {
            'course': self.course.id,
            'title': 'Setting Up Python Environment',
            'order': 1,
            'duration_minutes': 15,
            'content': 'Install Python 3.12, create virtualenv, and verify.',
            'video_url': 'https://www.youtube.com/embed/sample123',
            'is_preview': True
        }
        res = self.client.post(reverse('backend:lesson_create', args=[self.course.id]), lesson_data, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Lesson.objects.filter(title='Setting Up Python Environment', course=self.course).exists())
        lesson = Lesson.objects.get(title='Setting Up Python Environment', course=self.course)

        # Edit Lesson
        edit_data = {
            'course': self.course.id,
            'title': 'Setting Up Python Environment (Updated)',
            'order': 1,
            'duration_minutes': 20,
            'content': 'Updated content with pip and poetry.',
            'video_url': 'https://www.youtube.com/embed/sample123',
            'is_preview': True
        }
        res_edit = self.client.post(reverse('backend:lesson_edit', args=[lesson.id]), edit_data, follow=True)
        self.assertEqual(res_edit.status_code, 200)
        lesson.refresh_from_db()
        self.assertEqual(lesson.title, 'Setting Up Python Environment (Updated)')
        self.assertEqual(lesson.duration_minutes, 20)

        # Delete Lesson
        res_del = self.client.post(reverse('backend:lesson_delete', args=[lesson.id]), follow=True)
        self.assertEqual(res_del.status_code, 200)
        self.assertFalse(Lesson.objects.filter(id=lesson.id).exists())

    def test_category_crud(self):
        self.client.login(username='adminuser', password='adminpassword123')
        # View categories
        response = self.client.get(reverse('backend:categories_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Computer Science')

        # Create category
        cat_data = {
            'name': 'Cloud & DevOps',
            'icon': 'fa-cloud',
            'description': 'Docker, Kubernetes, and AWS architecture'
        }
        res = self.client.post(reverse('backend:category_create'), cat_data, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Category.objects.filter(name='Cloud & DevOps').exists())
        new_cat = Category.objects.get(name='Cloud & DevOps')

        # Edit category
        edit_data = {
            'name': 'Cloud Computing & DevOps',
            'icon': 'fa-cloud',
            'description': 'Updated cloud computing curriculum'
        }
        res_edit = self.client.post(reverse('backend:category_edit', args=[new_cat.id]), edit_data, follow=True)
        self.assertEqual(res_edit.status_code, 200)
        new_cat.refresh_from_db()
        self.assertEqual(new_cat.name, 'Cloud Computing & DevOps')

        # Delete category
        res_del = self.client.post(reverse('backend:category_delete', args=[new_cat.id]), follow=True)
        self.assertEqual(res_del.status_code, 200)
        self.assertFalse(Category.objects.filter(id=new_cat.id).exists())

    def test_enrollments_list(self):
        self.client.login(username='adminuser', password='adminpassword123')
        Enrollment.objects.create(user=self.student, course=self.course, progress=50, status='Active')
        response = self.client.get(reverse('backend:enrollments_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Intro to Python')
        self.assertContains(response, 'normalstudent')

    def test_contact_messages(self):
        self.client.login(username='adminuser', password='adminpassword123')
        msg = ContactMessage.objects.create(name='Alice', email='alice@test.com', message='Hello!')
        response = self.client.get(reverse('backend:messages_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice')
        self.assertContains(response, 'alice@test.com')

        # Toggle read status
        self.client.get(reverse('backend:message_toggle_read', args=[msg.id]))
        msg.refresh_from_db()
        self.assertTrue(msg.is_read)

    def test_instructor_role_and_isolation(self):
        # Create an instructor user (staff, not superuser)
        instructor = User.objects.create_user(
            username='instructor_jane',
            email='jane@zylora.com',
            password='janepassword123',
            first_name='Jane',
            last_name='Doe',
            is_staff=True,
            is_superuser=False
        )
        # Create course owned by this instructor
        jane_course = Course.objects.create(
            title='Machine Learning Foundations',
            instructor=instructor,
            category=self.category,
            description='Deep learning and neural networks.'
        )

        self.client.login(username='instructor_jane', password='janepassword123')

        # Instructor dashboard shows their course
        dash_res = self.client.get(reverse('backend:dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, 'Instructor Dashboard')
        self.assertContains(dash_res, 'My Courses')

        # Instructor courses list only shows their courses
        courses_res = self.client.get(reverse('backend:courses_list'))
        self.assertEqual(courses_res.status_code, 200)
        self.assertContains(courses_res, 'Machine Learning Foundations')
        self.assertNotContains(courses_res, 'Intro to Python')

        # Instructor CANNOT edit admin's course
        unauth_edit = self.client.get(reverse('backend:course_edit', args=[self.course.id]))
        self.assertEqual(unauth_edit.status_code, 302)

        # Instructor CAN edit their own course
        auth_edit = self.client.get(reverse('backend:course_edit', args=[jane_course.id]))
        self.assertEqual(auth_edit.status_code, 200)

    def test_admin_instructors_management(self):
        self.client.login(username='adminuser', password='adminpassword123')

        # View instructors list
        response = self.client.get(reverse('backend:instructors_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Instructors & Faculty')

        # Create new instructor
        inst_data = {
            'first_name': 'Robert',
            'last_name': 'Kaufman',
            'username': 'robertk',
            'email': 'robert@zylora.com',
            'password': 'robertpass123',
        }
        res_create = self.client.post(reverse('backend:instructor_create'), inst_data, follow=True)
        self.assertEqual(res_create.status_code, 200)
        self.assertTrue(User.objects.filter(username='robertk', is_staff=True).exists())
        new_inst = User.objects.get(username='robertk')

        # Toggle instructor status
        res_toggle = self.client.get(reverse('backend:instructor_toggle_status', args=[new_inst.id]), follow=True)
        self.assertEqual(res_toggle.status_code, 200)
        new_inst.refresh_from_db()
        self.assertFalse(new_inst.is_active)

    def test_reviews_management(self):
        from backend.models import CourseReview
        self.client.login(username='adminuser', password='adminpassword123')

        # Create review
        review = CourseReview.objects.create(
            course=self.course,
            student=self.student,
            rating=5,
            comment='Outstanding course with practical examples!'
        )

        # View reviews list
        response = self.client.get(reverse('backend:reviews_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Outstanding course with practical examples!')
        self.assertContains(response, self.course.title)

        # Delete review
        res_del = self.client.post(reverse('backend:review_delete', args=[review.id]), follow=True)
        self.assertEqual(res_del.status_code, 200)
        self.assertFalse(CourseReview.objects.filter(id=review.id).exists())

    def test_enrollment_progress_detail(self):
        from backend.models import Lesson, LessonProgress
        self.client.login(username='adminuser', password='adminpassword123')

        lesson = Lesson.objects.create(course=self.course, title='Lesson 1: Basics', order=1)
        enr = Enrollment.objects.create(user=self.student, course=self.course, progress=100, status='Completed')
        LessonProgress.objects.create(student=self.student, lesson=lesson, is_completed=True)

        detail_url = reverse('backend:enrollment_detail', args=[enr.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lesson-by-Lesson Progress')
        self.assertContains(response, 'Lesson 1: Basics')
        self.assertContains(response, 'Completed')

