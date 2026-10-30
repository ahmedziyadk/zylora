from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from backend.models import Category, Course, Lesson, Enrollment, LessonProgress, CourseReview, ContactMessage
from frontend.models import StudentProfile


class FrontendAuthAndPagesTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_index_page(self):
        response = self.client.get(reverse('frontend:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Zylora')

    def test_about_page(self):
        response = self.client.get(reverse('frontend:about'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Zylora')

    def test_courses_page(self):
        response = self.client.get(reverse('frontend:courses'))
        self.assertEqual(response.status_code, 200)

    def test_blog_page(self):
        response = self.client.get(reverse('frontend:blog'))
        self.assertEqual(response.status_code, 200)

    def test_blog_single_page(self):
        response = self.client.get(reverse('frontend:blog_single'))
        self.assertEqual(response.status_code, 200)

    def test_contact_page_get_and_post(self):
        # GET contact
        response = self.client.get(reverse('frontend:contact'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Send Us a Message')

        # POST contact inquiry
        post_data = {
            'name': 'Jane Doe',
            'email': 'jane@example.com',
            'subject': 'Course Syllabus Question',
            'message': 'Could you please send me more information regarding the curriculum?'
        }
        res_post = self.client.post(reverse('frontend:contact'), post_data, follow=True)
        self.assertEqual(res_post.status_code, 200)
        self.assertTrue(ContactMessage.objects.filter(email='jane@example.com').exists())

    def test_visitor_navigation(self):
        response = self.client.get(reverse('frontend:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'<div class="login_button"><a href="{reverse("frontend:login")}">Login</a></div>')
        self.assertContains(response, f'<div class="login_button ml-2"><a href="{reverse("frontend:register")}">Register</a></div>')
        self.assertNotContains(response, 'Admin Panel')
        self.assertNotContains(response, 'Admin Dashboard')
        self.assertNotContains(response, 'My Learning')

    def test_student_navigation_strictly_hides_admin_links(self):
        student = User.objects.create_user(username='nav_student', password='password123', first_name='Ziyad')
        self.client.login(username='nav_student', password='password123')
        response = self.client.get(reverse('frontend:index'))
        self.assertEqual(response.status_code, 200)
        # Student options present
        self.assertContains(response, 'My Learning')
        self.assertContains(response, 'My Profile')
        self.assertContains(response, 'Logout')
        self.assertContains(response, 'Ziyad')
        # Admin options MUST NOT be displayed
        self.assertNotContains(response, 'Admin Panel')
        self.assertNotContains(response, 'Admin Dashboard')
        self.assertNotContains(response, reverse('backend:dashboard'))
        self.assertNotContains(response, reverse('backend:admin_login'))
        # No visitor login/register button
        self.assertNotContains(response, f'<a href="{reverse("frontend:login")}">Login</a>')

    def test_admin_navigation_displays_admin_links_and_hides_student_options(self):
        admin = User.objects.create_superuser(username='nav_admin', password='password123', first_name='SuperAdmin')
        self.client.login(username='nav_admin', password='password123')
        response = self.client.get(reverse('frontend:index'))
        self.assertEqual(response.status_code, 200)
        # Admin options present
        self.assertContains(response, 'Admin Panel')
        self.assertContains(response, 'Admin Dashboard')
        self.assertContains(response, 'Logout')
        self.assertContains(response, 'SuperAdmin (Admin)')
        # Student specific options absent
        self.assertNotContains(response, 'My Learning')
        self.assertNotContains(response, 'My Profile')
        # No visitor login/register button
        self.assertNotContains(response, f'<a href="{reverse("frontend:login")}">Login</a>')

    def test_login_page_renders_unified_portal(self):
        response = self.client.get(reverse('frontend:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome to Zylora')
        self.assertContains(response, 'Unified Portal for Students &amp; Administrators')
        self.assertContains(response, 'id="togglePasswordBtn"')
        self.assertContains(response, reverse('frontend:password_reset'))
        self.assertContains(response, reverse('frontend:register'))

    def test_register_page_renders_with_full_name(self):
        response = self.client.get(reverse('frontend:register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Student Registration')
        self.assertContains(response, 'Public Registration is for Students Only')
        self.assertContains(response, 'id="id_full_name"')
        self.assertContains(response, 'toggleRegPasswordBtn')
        self.assertContains(response, reverse('frontend:login'))

    def test_student_registration_with_full_name_success(self):
        data = {
            'full_name': 'Alex Morgan',
            'username': 'alexmorgan',
            'email': 'alex@example.com',
            'phone': '1234567890',
            'password': 'password123',
            'confirm_password': 'password123',
        }
        response = self.client.post(reverse('frontend:register'), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='alexmorgan').exists())
        user = User.objects.get(username='alexmorgan')
        self.assertEqual(user.first_name, 'Alex')
        self.assertEqual(user.last_name, 'Morgan')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())
        self.assertEqual(user.student_profile.phone, '1234567890')
        self.assertContains(response, 'Welcome back, Alex Morgan!')

    def test_student_registration_privilege_escalation_blocked(self):
        data = {
            'full_name': 'Hacker Student',
            'username': 'hackerstudent',
            'email': 'hacker@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'is_staff': True,
            'is_superuser': True,
        }
        response = self.client.post(reverse('frontend:register'), data, follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username='hackerstudent')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_student_registration_password_mismatch(self):
        data = {
            'full_name': 'Alex Morgan',
            'username': 'alexmorgan2',
            'email': 'alex2@example.com',
            'phone': '1234567890',
            'password': 'password123',
            'confirm_password': 'mismatchedpass',
        }
        response = self.client.post(reverse('frontend:register'), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='alexmorgan2').exists())
        self.assertContains(response, 'Passwords do not match')

    def test_student_registration_duplicate_username(self):
        User.objects.create_user(username='existinguser', password='password123')
        data = {
            'full_name': 'New User',
            'username': 'existinguser',
            'email': 'new@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
        }
        response = self.client.post(reverse('frontend:register'), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already taken')

    def test_student_login_with_username(self):
        User.objects.create_user(username='student1', password='mypassword123', first_name='John')
        response = self.client.post(reverse('frontend:login'), {
            'username': 'student1',
            'password': 'mypassword123',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back, John!')
        # Landed on student dashboard
        self.assertEqual(response.redirect_chain[-1][0], reverse('frontend:dashboard'))

    def test_student_login_with_email(self):
        User.objects.create_user(username='student2', email='student2@test.com', password='mypassword123', first_name='Emma')
        response = self.client.post(reverse('frontend:login'), {
            'username': 'student2@test.com',
            'password': 'mypassword123',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back, Emma!')
        self.assertEqual(response.redirect_chain[-1][0], reverse('frontend:dashboard'))

    def test_admin_login_via_unified_login_redirects_to_admin_dashboard(self):
        User.objects.create_superuser(
            username='superadmin',
            email='superadmin@zylora.com',
            password='adminpassword123',
            first_name='Admin'
        )
        response = self.client.post(reverse('frontend:login'), {
            'username': 'superadmin',
            'password': 'adminpassword123',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Platform Overview')
        self.assertEqual(response.redirect_chain[-1][0], reverse('backend:dashboard'))

    def test_instructor_login_via_unified_login_redirects_to_admin_dashboard(self):
        User.objects.create_user(
            username='instructor_user',
            email='instructor@zylora.com',
            password='instructorpass',
            is_staff=True,
            first_name='Instructor'
        )
        response = self.client.post(reverse('frontend:login'), {
            'username': 'instructor_user',
            'password': 'instructorpass',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Instructor Dashboard')
        self.assertEqual(response.redirect_chain[-1][0], reverse('backend:dashboard'))

    def test_authenticated_admin_visiting_login_redirects_to_admin_dashboard(self):
        admin = User.objects.create_superuser(username='admin_visiting', password='password123')
        self.client.login(username='admin_visiting', password='password123')
        response = self.client.get(reverse('frontend:login'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('backend:dashboard'))

    def test_authenticated_student_visiting_login_redirects_to_student_dashboard(self):
        student = User.objects.create_user(username='student_visiting', password='password123')
        self.client.login(username='student_visiting', password='password123')
        response = self.client.get(reverse('frontend:login'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('frontend:dashboard'))

    def test_authenticated_admin_visiting_register_redirects_to_admin_dashboard(self):
        admin = User.objects.create_superuser(username='admin_reg_visiting', password='password123')
        self.client.login(username='admin_reg_visiting', password='password123')
        response = self.client.get(reverse('frontend:register'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('backend:dashboard'))

    def test_authenticated_student_visiting_register_redirects_to_student_dashboard(self):
        student = User.objects.create_user(username='student_reg_visiting', password='password123')
        self.client.login(username='student_reg_visiting', password='password123')
        response = self.client.get(reverse('frontend:register'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('frontend:dashboard'))

    def test_student_login_with_admin_next_url_is_safely_ignored(self):
        User.objects.create_user(username='student_sneaky', password='password123')
        response = self.client.post(f"{reverse('frontend:login')}?next={reverse('backend:dashboard')}", {
            'username': 'student_sneaky',
            'password': 'password123',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        # Should be directed to student dashboard, NOT backend:dashboard
        self.assertEqual(response.redirect_chain[-1][0], reverse('frontend:dashboard'))

    def test_admin_login_with_next_url_is_honored(self):
        User.objects.create_superuser(username='admin_next', password='password123')
        target_url = reverse('backend:courses_list')
        response = self.client.post(f"{reverse('frontend:login')}?next={target_url}", {
            'username': 'admin_next',
            'password': 'password123',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1][0], target_url)

    def test_deactivated_student_cannot_login(self):
        User.objects.create_user(username='inactive_student', password='password123', is_active=False)
        response = self.client.post(reverse('frontend:login'), {
            'username': 'inactive_student',
            'password': 'password123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This account is currently inactive')

    def test_student_login_invalid_credentials(self):
        response = self.client.post(reverse('frontend:login'), {
            'username': 'nonexistent',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username/email or password')

    def test_student_cannot_access_admin_dashboard_urls(self):
        User.objects.create_user(username='plainstudent', password='password123')
        self.client.login(username='plainstudent', password='password123')
        # Attempt to access backend admin panel
        response = self.client.get(reverse('backend:dashboard'), follow=True)
        self.assertEqual(response.status_code, 200)
        # Verify student was blocked and bounced back to student dashboard with access denied error
        self.assertContains(response, 'Access denied. Administrator privileges required.')
        self.assertContains(response, 'Student Dashboard')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('frontend:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('frontend:login'), response.url)

    def test_student_logout(self):
        user = User.objects.create_user(username='student3', password='mypassword123')
        self.client.login(username='student3', password='mypassword123')
        response = self.client.get(reverse('frontend:logout'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('frontend:login'))


class CourseAndLMSWorkflowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(
            username='learner1',
            email='learner1@zylora.com',
            password='learnerpass123',
            first_name='David',
            last_name='Miller'
        )
        StudentProfile.objects.create(
            user=self.student,
            phone='555-0199',
            headline='Aspiring Python Developer'
        )

        self.category = Category.objects.create(
            name='Software Engineering',
            icon='fa-code',
            description='Computer science and modern engineering curricula.'
        )

        # Published course
        self.published_course = Course.objects.create(
            title='Python Programming Masterclass',
            slug='python-programming-masterclass',
            category=self.category,
            instructor_name='Prof. Alan Turing',
            price=0.00,
            level='Beginner',
            duration_weeks=6,
            description='Comprehensive introduction to Python and modern software craftsmanship.',
            is_published=True,
            is_featured=True
        )

        # Unpublished draft course
        self.draft_course = Course.objects.create(
            title='Draft Advanced Cryptography',
            slug='draft-advanced-cryptography',
            category=self.category,
            instructor_name='Prof. Secret',
            price=99.00,
            level='Advanced',
            duration_weeks=8,
            description='Not ready for public access.',
            is_published=False
        )

        # Lessons for published course
        self.lesson_preview = Lesson.objects.create(
            course=self.published_course,
            title='Lesson 1: Introduction to Python & Tooling',
            order=1,
            duration_minutes=20,
            content='Welcome to Python! In this lecture we install Python and set up VS Code.',
            video_url='https://www.youtube.com/embed/sample-video-1',
            is_preview=True
        )

        self.lesson_locked = Lesson.objects.create(
            course=self.published_course,
            title='Lesson 2: Data Structures & Algorithms',
            order=2,
            duration_minutes=45,
            content='Deep dive into Python lists, dictionaries, tuples, and sets.',
            video_url='https://www.youtube.com/embed/sample-video-2',
            is_preview=False
        )

    def test_admin_frontend_synchronization(self):
        # 1. Published course appears in courses page
        res = self.client.get(reverse('frontend:courses'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Python Programming Masterclass')
        # Draft course must not appear
        self.assertNotContains(res, 'Draft Advanced Cryptography')

        # 2. When admin unpublishes course, it disappears from public view
        self.published_course.is_published = False
        self.published_course.save()

        res_after = self.client.get(reverse('frontend:courses'))
        self.assertEqual(res_after.status_code, 200)
        self.assertNotContains(res_after, 'Python Programming Masterclass')

    def test_courses_search_and_filters(self):
        # Search by keyword
        res_search = self.client.get(reverse('frontend:courses'), {'q': 'Python'})
        self.assertEqual(res_search.status_code, 200)
        self.assertContains(res_search, 'Python Programming Masterclass')

        res_search_none = self.client.get(reverse('frontend:courses'), {'q': 'NonExistentKeyword'})
        self.assertEqual(res_search_none.status_code, 200)
        self.assertContains(res_search_none, 'No Courses Found')

        # Filter by Category
        res_cat = self.client.get(reverse('frontend:courses'), {'category': self.category.id})
        self.assertEqual(res_cat.status_code, 200)
        self.assertContains(res_cat, 'Python Programming Masterclass')

        # Filter by Level
        res_level = self.client.get(reverse('frontend:courses'), {'level': 'Beginner'})
        self.assertEqual(res_level.status_code, 200)
        self.assertContains(res_level, 'Python Programming Masterclass')

        # Filter by Price (Free)
        res_free = self.client.get(reverse('frontend:courses'), {'price': 'free'})
        self.assertEqual(res_free.status_code, 200)
        self.assertContains(res_free, 'Python Programming Masterclass')

        # Filter by Price (Paid)
        res_paid = self.client.get(reverse('frontend:courses'), {'price': 'paid'})
        self.assertEqual(res_paid.status_code, 200)
        self.assertEqual(len(res_paid.context['courses']), 0)
        self.assertContains(res_paid, 'No Courses Found')

    def test_course_detail_page_and_curriculum(self):
        url = reverse('frontend:course_detail', kwargs={'slug': self.published_course.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python Programming Masterclass')
        self.assertContains(response, 'Prof. Alan Turing')
        self.assertContains(response, 'Introduction to Python')
        self.assertContains(response, 'Data Structures &amp; Algorithms')

    def test_student_enrollment_and_duplicate_prevention(self):
        self.client.login(username='learner1', password='learnerpass123')
        enroll_url = reverse('frontend:enroll_course', kwargs={'slug': self.published_course.slug})

        # Initial Enrollment
        res = self.client.post(enroll_url, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Enrollment.objects.filter(user=self.student, course=self.published_course).exists())
        enrollment = Enrollment.objects.get(user=self.student, course=self.published_course)
        self.assertEqual(enrollment.progress, 0)
        self.assertEqual(enrollment.status, 'Active')

        # Prevent duplicate enrollment
        res_dup = self.client.post(enroll_url, follow=True)
        self.assertEqual(res_dup.status_code, 200)
        self.assertEqual(Enrollment.objects.filter(user=self.student, course=self.published_course).count(), 1)
        self.assertContains(res_dup, 'already enrolled')

    def test_lesson_access_permissions(self):
        locked_url = reverse('frontend:lesson_learning', kwargs={
            'slug': self.published_course.slug,
            'lesson_id': self.lesson_locked.id
        })
        preview_url = reverse('frontend:lesson_learning', kwargs={
            'slug': self.published_course.slug,
            'lesson_id': self.lesson_preview.id
        })

        # 1. Anonymous user cannot access locked lesson (redirects to login)
        res_anon_locked = self.client.get(locked_url)
        self.assertEqual(res_anon_locked.status_code, 302)
        self.assertIn(reverse('frontend:login'), res_anon_locked.url)

        # 2. Anonymous user CAN access preview lesson
        res_preview = self.client.get(preview_url)
        self.assertEqual(res_preview.status_code, 200)
        self.assertContains(res_preview, 'Introduction to Python')

        # 3. Non-enrolled logged-in user cannot access locked lesson (redirects to course detail)
        self.client.login(username='learner1', password='learnerpass123')
        res_non_enrolled = self.client.get(locked_url, follow=True)
        self.assertEqual(res_non_enrolled.status_code, 200)
        self.assertContains(res_non_enrolled, 'You must enroll in this course to access this lesson.')

        # 4. Enrolled student can access locked lesson
        Enrollment.objects.create(user=self.student, course=self.published_course)
        res_enrolled = self.client.get(locked_url)
        self.assertEqual(res_enrolled.status_code, 200)
        self.assertContains(res_enrolled, 'Data Structures')

    def test_lesson_completion_and_progress_recalculation(self):
        enrollment = Enrollment.objects.create(user=self.student, course=self.published_course, progress=0)
        self.client.login(username='learner1', password='learnerpass123')

        toggle_url_1 = reverse('frontend:toggle_lesson_completion', kwargs={
            'slug': self.published_course.slug,
            'lesson_id': self.lesson_preview.id
        })

        # Mark lesson 1 complete (1 of 2 -> 50%)
        res1 = self.client.post(toggle_url_1, follow=True)
        self.assertEqual(res1.status_code, 200)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.progress, 50)
        self.assertEqual(enrollment.status, 'Active')
        self.assertTrue(LessonProgress.objects.filter(student=self.student, lesson=self.lesson_preview, is_completed=True).exists())

        # Mark lesson 2 complete (2 of 2 -> 100% Completed)
        toggle_url_2 = reverse('frontend:toggle_lesson_completion', kwargs={
            'slug': self.published_course.slug,
            'lesson_id': self.lesson_locked.id
        })
        res2 = self.client.post(toggle_url_2, follow=True)
        self.assertEqual(res2.status_code, 200)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.progress, 100)
        self.assertEqual(enrollment.status, 'Completed')

        # Check student dashboard reflects 100%
        dash_res = self.client.get(reverse('frontend:dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, '100%')
        self.assertContains(dash_res, 'Completed')

    def test_course_review_submission(self):
        self.client.login(username='learner1', password='learnerpass123')
        review_url = reverse('frontend:add_course_review', kwargs={'slug': self.published_course.slug})

        # Non-enrolled student cannot leave review
        res_unauth = self.client.post(review_url, {'rating': 5, 'comment': 'Great course!'}, follow=True)
        self.assertEqual(res_unauth.status_code, 200)
        self.assertFalse(CourseReview.objects.filter(student=self.student).exists())

        # Enrolled student can leave review
        Enrollment.objects.create(user=self.student, course=self.published_course)
        res_auth = self.client.post(review_url, {'rating': 5, 'comment': 'Exceptional course, clear explanations!'}, follow=True)
        self.assertEqual(res_auth.status_code, 200)
        self.assertTrue(CourseReview.objects.filter(student=self.student, course=self.published_course).exists())
        review = CourseReview.objects.get(student=self.student, course=self.published_course)
        self.assertEqual(review.rating, 5)

        # Course detail displays the review
        detail_res = self.client.get(reverse('frontend:course_detail', kwargs={'slug': self.published_course.slug}))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, 'Exceptional course, clear explanations!')

    def test_student_profile_update(self):
        self.client.login(username='learner1', password='learnerpass123')
        update_url = reverse('frontend:profile_update')

        post_data = {
            'first_name': 'David Jonathan',
            'last_name': 'Miller',
            'email': 'david.miller@newdomain.com',
            'phone': '+1 (555) 987-6543',
            'headline': 'Senior Full-Stack Cloud Engineer',
            'bio': 'Passionate about distributed systems and learning online.'
        }
        response = self.client.post(update_url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, 'David Jonathan')
        self.assertEqual(self.student.email, 'david.miller@newdomain.com')
        self.assertEqual(self.student.student_profile.phone, '+1 (555) 987-6543')
        self.assertEqual(self.student.student_profile.headline, 'Senior Full-Stack Cloud Engineer')
        self.assertContains(response, 'Your profile details have been updated successfully.')

    def test_student_password_change_success(self):
        self.client.login(username='learner1', password='learnerpass123')
        change_url = reverse('frontend:password_change')
        post_data = {
            'current_password': 'learnerpass123',
            'new_password': 'newsecretpass456',
            'confirm_new_password': 'newsecretpass456',
        }
        response = self.client.post(change_url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password('newsecretpass456'))
        self.assertContains(response, 'Your password has been changed successfully.')

    def test_student_password_change_invalid_current_password(self):
        self.client.login(username='learner1', password='learnerpass123')
        change_url = reverse('frontend:password_change')
        post_data = {
            'current_password': 'wrongpassword',
            'new_password': 'newsecretpass456',
            'confirm_new_password': 'newsecretpass456',
        }
        response = self.client.post(change_url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertFalse(self.student.check_password('newsecretpass456'))
        self.assertContains(response, 'Current password is incorrect.')

    def test_password_reset_flow(self):
        # GET password reset page
        response = self.client.get(reverse('frontend:password_reset'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forgot Password?')

        # POST email to request reset
        post_data = {'email': self.student.email}
        res_post = self.client.post(reverse('frontend:password_reset'), post_data, follow=True)
        self.assertEqual(res_post.status_code, 200)
        self.assertContains(res_post, 'Check Your Email')


class LessonLearningWorkflowTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Design & AI', slug='design-ai')
        self.instructor = User.objects.create_user(
            username='prof_smith',
            email='smith@zylora.com',
            password='smithpass123'
        )
        self.course = Course.objects.create(
            title='Graphic Designing & AI',
            slug='graphic-designing-ai',
            category=self.category,
            instructor=self.instructor,
            instructor_name='Professor Smith',
            price=49.99,
            is_published=True
        )
        # Lesson 1: YouTube short URL (preview)
        self.lesson1 = Lesson.objects.create(
            course=self.course,
            title='Photoshop Mastery',
            video_url='https://youtu.be/OKkWRpoIFuw?si=sampleSiTag',
            order=1,
            duration_minutes=25,
            content='Master Photoshop selections, layers, and masking.',
            is_preview=True
        )
        # Lesson 2: Direct MP4 video (enrolled only)
        self.lesson2 = Lesson.objects.create(
            course=self.course,
            title='Adobe Premiere Pro',
            video_url='https://example.com/videos/premiere.mp4',
            order=2,
            duration_minutes=40,
            content='Timeline editing, color grading, and video transitions.',
            is_preview=False
        )
        # Lesson 3: Notes-only lesson (enrolled only)
        self.lesson3 = Lesson.objects.create(
            course=self.course,
            title='Design Theory & Ethics',
            video_url='',
            order=3,
            duration_minutes=15,
            content='Typography principles, color harmonies, and AI copyright.',
            is_preview=False
        )
        # Lesson 4: External non-embeddable link
        self.lesson4 = Lesson.objects.create(
            course=self.course,
            title='External Portfolio Lab',
            video_url='https://externallab.com/interactive-workshop',
            order=4,
            duration_minutes=30,
            content='External design laboratory walkthrough.',
            is_preview=False
        )

        self.student = User.objects.create_user(
            username='design_student',
            email='student@zylora.com',
            password='studentpass123'
        )
        self.enrollment = Enrollment.objects.create(
            user=self.student,
            course=self.course,
            progress=0,
            status='Active'
        )

    def test_lesson_learning_page_renders_with_assets_and_data(self):
        self.client.login(username='design_student', password='studentpass123')
        url = reverse('frontend:lesson_learning', kwargs={'slug': self.course.slug, 'lesson_id': self.lesson1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Verify static CSS and JS are included
        self.assertContains(response, 'frontend/styles/courses.css')
        self.assertContains(response, 'frontend/styles/courses_responsive.css')
        self.assertContains(response, 'frontend/js/courses.js')

        # Verify database-driven course and lesson information
        self.assertContains(response, 'Graphic Designing &amp; AI')
        self.assertContains(response, 'Photoshop Mastery')
        self.assertContains(response, 'Professor Smith')
        self.assertContains(response, 'Design &amp; AI')
        self.assertContains(response, 'Lesson #1')
        self.assertContains(response, 'Course Curriculum')
        self.assertContains(response, '4 total lessons')

    def test_youtube_url_converts_to_embed_iframe(self):
        self.client.login(username='design_student', password='studentpass123')
        url = reverse('frontend:lesson_learning', kwargs={'slug': self.course.slug, 'lesson_id': self.lesson1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Converted YouTube embed URL inside iframe
        expected_embed = 'https://www.youtube.com/embed/OKkWRpoIFuw'
        self.assertEqual(self.lesson1.embed_video_url, expected_embed)
        self.assertContains(response, f'src="{expected_embed}"')
        self.assertContains(response, '<iframe')
        self.assertContains(response, 'allowfullscreen')

    def test_direct_video_mp4_renders_html5_player(self):
        self.client.login(username='design_student', password='studentpass123')
        url = reverse('frontend:lesson_learning', kwargs={'slug': self.course.slug, 'lesson_id': self.lesson2.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertTrue(self.lesson2.is_direct_video)
        self.assertContains(response, '<video controls')
        self.assertContains(response, 'src="https://example.com/videos/premiere.mp4"')

    def test_notes_only_lesson_renders_reading_module(self):
        self.client.login(username='design_student', password='studentpass123')
        url = reverse('frontend:lesson_learning', kwargs={'slug': self.course.slug, 'lesson_id': self.lesson3.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertFalse(self.lesson3.has_valid_video)
        self.assertContains(response, 'Interactive Reading &amp; Lecture Notes Module')
        self.assertContains(response, 'Typography principles, color harmonies, and AI copyright.')

    def test_external_unsupported_link_renders_safe_external_notice(self):
        self.client.login(username='design_student', password='studentpass123')
        url = reverse('frontend:lesson_learning', kwargs={'slug': self.course.slug, 'lesson_id': self.lesson4.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'External Video Resource')
        self.assertContains(response, 'Open Video Link')
        self.assertContains(response, 'https://externallab.com/interactive-workshop')

    def test_lesson_completion_toggle_updates_progress_and_autoadvances(self):
        self.client.login(username='design_student', password='studentpass123')
        toggle_url = reverse('frontend:toggle_lesson_completion', kwargs={'slug': self.course.slug, 'lesson_id': self.lesson1.id})

        # Mark Lesson 1 as completed -> should auto advance to Lesson 2
        response = self.client.post(toggle_url, follow=True)
        self.assertEqual(response.status_code, 200)

        self.enrollment.refresh_from_db()
        # 1 out of 4 lessons completed = 25%
        self.assertEqual(self.enrollment.progress, 25)
        self.assertEqual(self.enrollment.status, 'Active')
        self.assertContains(response, "marked complete! Progress: 25%")

        # Verify auto-advance redirect was to Lesson 2
        self.assertContains(response, 'Adobe Premiere Pro')

        # Toggle again to undo completion -> should recalculate to 0%
        undo_response = self.client.post(toggle_url, follow=True)
        self.assertEqual(undo_response.status_code, 200)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.progress, 0)
        self.assertContains(undo_response, "marked as incomplete")

    def test_course_learn_url_without_lesson_id_resumes_incomplete_lesson(self):
        self.client.login(username='design_student', password='studentpass123')
        # Mark Lesson 1 as done
        LessonProgress.objects.create(student=self.student, lesson=self.lesson1, is_completed=True)
        self.enrollment.recalculate_progress()

        # Access /courses/<slug>/learn/ without lesson_id
        url = reverse('frontend:course_learn', kwargs={'slug': self.course.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Should resume at Lesson 2 (the first incomplete lesson)
        self.assertEqual(response.context['lesson'].id, self.lesson2.id)
        self.assertContains(response, 'Adobe Premiere Pro')

    def test_unenrolled_student_cannot_access_locked_lesson(self):
        other_user = User.objects.create_user(
            username='other_student',
            email='other@zylora.com',
            password='otherpass123'
        )
        self.client.login(username='other_student', password='otherpass123')

        # Lesson 2 is not preview, other_user is not enrolled
        locked_url = reverse('frontend:lesson_learning', kwargs={'slug': self.course.slug, 'lesson_id': self.lesson2.id})
        response = self.client.get(locked_url, follow=True)
        self.assertEqual(response.status_code, 200)

        # Redirected to course detail with warning message
        self.assertContains(response, 'You must enroll in this course to access this lesson.')

        # Lesson 1 is preview -> other_user CAN access
        preview_url = reverse('frontend:lesson_learning', kwargs={'slug': self.course.slug, 'lesson_id': self.lesson1.id})
        res_preview = self.client.get(preview_url)
        self.assertEqual(res_preview.status_code, 200)
        self.assertContains(res_preview, 'Free Preview Mode')



