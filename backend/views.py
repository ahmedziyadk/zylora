from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db.models import Count, Q

from .models import Category, Course, Enrollment, ContactMessage, Lesson, LessonProgress, CourseReview
from .forms import AdminLoginForm, CourseForm, CategoryForm, StudentEditForm, LessonForm, InstructorForm
from frontend.models import StudentProfile


def is_admin_user(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def is_superuser(user):
    return user.is_authenticated and user.is_superuser


def admin_login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('backend:dashboard')
        else:
            messages.error(request, "Access denied. Administrator privileges required.")
            return redirect('frontend:dashboard')

    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            login_input = form.cleaned_data['username'].strip()
            password = form.cleaned_data['password']

            user = authenticate(request, username=login_input, password=password)
            if user is None and '@' in login_input:
                try:
                    user_obj = User.objects.get(email__iexact=login_input)
                    user = authenticate(request, username=user_obj.username, password=password)
                except (User.DoesNotExist, User.MultipleObjectsReturned):
                    user = None

            if user is not None and user.is_staff:
                login(request, user)
                role = "Administrator" if user.is_superuser else "Instructor"
                messages.success(request, f"Welcome to the Zylora {role} Portal, {user.first_name or user.username}!")
                next_url = request.GET.get('next') or 'backend:dashboard'
                return redirect(next_url)
            else:
                messages.error(request, "Access denied. Valid staff or instructor credentials required.")
    else:
        form = AdminLoginForm()

    return render(request, 'backend/admin_login.html', {'form': form})


def admin_logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "You have been signed out of the Admin Portal.")
    return redirect('backend:admin_login')


@user_passes_test(is_admin_user, login_url='backend:admin_login')
def dashboard_overview(request):
    is_instructor = not request.user.is_superuser

    if is_instructor:
        instructor_courses = Course.objects.filter(instructor=request.user)
        total_courses = instructor_courses.count()
        total_students = User.objects.filter(enrollments__course__in=instructor_courses).distinct().count()
        total_enrollments = Enrollment.objects.filter(course__in=instructor_courses).count()
        active_enrollments = Enrollment.objects.filter(course__in=instructor_courses, status='Active').count()
        total_lessons = Lesson.objects.filter(course__in=instructor_courses).count()
        unread_messages = ContactMessage.objects.filter(is_read=False).count()

        recent_students = User.objects.filter(enrollments__course__in=instructor_courses).distinct().order_by('-date_joined')[:5]
        recent_enrollments = Enrollment.objects.filter(course__in=instructor_courses).select_related('user', 'course').order_by('-enrolled_at')[:5]
        recent_messages = ContactMessage.objects.order_by('-created_at')[:5]
        categories = Category.objects.filter(courses__in=instructor_courses).distinct().annotate(
            course_count=Count('courses', filter=Q(courses__instructor=request.user))
        )
    else:
        total_students = User.objects.filter(is_staff=False).count()
        total_courses = Course.objects.count()
        total_enrollments = Enrollment.objects.count()
        active_enrollments = Enrollment.objects.filter(status='Active').count()
        total_lessons = Lesson.objects.count()
        unread_messages = ContactMessage.objects.filter(is_read=False).count()

        recent_students = User.objects.filter(is_staff=False).order_by('-date_joined')[:5]
        recent_enrollments = Enrollment.objects.select_related('user', 'course').order_by('-enrolled_at')[:5]
        recent_messages = ContactMessage.objects.order_by('-created_at')[:5]
        categories = Category.objects.annotate(course_count=Count('courses'))

    context = {
        'total_students': total_students,
        'total_courses': total_courses,
        'total_enrollments': total_enrollments,
        'active_enrollments': active_enrollments,
        'total_lessons': total_lessons,
        'unread_messages': unread_messages,
        'recent_students': recent_students,
        'recent_enrollments': recent_enrollments,
        'recent_messages': recent_messages,
        'categories': categories,
        'is_instructor': is_instructor,
    }
    return render(request, 'backend/dashboard.html', context)


@user_passes_test(is_admin_user, login_url='backend:admin_login')
def students_list(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if not request.user.is_superuser:
        students = User.objects.filter(
            is_staff=False,
            enrollments__course__instructor=request.user
        ).distinct().select_related('student_profile').order_by('-date_joined')
    else:
        students = User.objects.filter(is_staff=False).select_related('student_profile').order_by('-date_joined')

    if query:
        students = students.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(student_profile__phone__icontains=query)
        )

    if status_filter == 'active':
        students = students.filter(is_active=True)
    elif status_filter == 'inactive':
        students = students.filter(is_active=False)

    context = {
        'students': students,
        'query': query,
        'status_filter': status_filter,
        'total_count': students.count(),
        'is_superuser': request.user.is_superuser,
    }
    return render(request, 'backend/students_list.html', context)


@user_passes_test(is_superuser, login_url='backend:admin_login')
def student_toggle_status(request, user_id):
    student = get_object_or_404(User, id=user_id, is_staff=False)
    student.is_active = not student.is_active
    student.save()
    status_str = "activated" if student.is_active else "suspended"
    messages.success(request, f"Student account for {student.username} has been {status_str}.")
    return redirect('backend:students_list')


@user_passes_test(is_superuser, login_url='backend:admin_login')
def student_delete(request, user_id):
    student = get_object_or_404(User, id=user_id, is_staff=False)
    if request.method == 'POST':
        username = student.username
        student.delete()
        messages.success(request, f"Student account '{username}' was permanently deleted.")
        return redirect('backend:students_list')
    return render(request, 'backend/confirm_delete.html', {
        'object_name': f"Student: {student.get_full_name() or student.username}",
        'cancel_url': 'backend:students_list',
    })


@user_passes_test(is_admin_user, login_url='backend:admin_login')
def courses_list(request):
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()

    courses = Course.objects.select_related('category').annotate(
        enrollment_count=Count('enrollments', distinct=True),
        lesson_count_annotated=Count('lessons', distinct=True)
    ).order_by('-created_at')

    if not request.user.is_superuser:
        courses = courses.filter(instructor=request.user)

    if query:
        courses = courses.filter(
            Q(title__icontains=query) |
            Q(instructor_name__icontains=query) |
            Q(description__icontains=query)
        )

    if category_id:
        courses = courses.filter(category_id=category_id)

    categories = Category.objects.all()

    context = {
        'courses': courses,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
        'total_count': courses.count(),
        'is_instructor': not request.user.is_superuser,
    }
    return render(request, 'backend/courses_list.html', context)


@user_passes_test(is_admin_user, login_url='backend:admin_login')
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            if not request.user.is_superuser:
                course.instructor = request.user
                course.instructor_name = request.user.get_full_name() or request.user.username
            elif not course.instructor and not course.instructor_name:
                course.instructor = request.user
                course.instructor_name = request.user.get_full_name() or request.user.username
            course.save()
            messages.success(request, f"Course '{course.title}' was created successfully!")
            return redirect('backend:courses_list')
    else:
        initial = {}
        if not request.user.is_superuser:
            initial['instructor'] = request.user
            initial['instructor_name'] = request.user.get_full_name() or request.user.username
        form = CourseForm(initial=initial)

    return render(request, 'backend/course_form.html', {'form': form, 'title': 'Create New Course'})


@user_passes_test(is_admin_user, login_url='backend:admin_login')
def course_edit(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not request.user.is_superuser and course.instructor != request.user:
        messages.error(request, "Permission denied. You can only modify your own courses.")
        return redirect('backend:courses_list')

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            updated_course = form.save(commit=False)
            if not request.user.is_superuser:
                updated_course.instructor = request.user
                updated_course.instructor_name = request.user.get_full_name() or request.user.username
            updated_course.save()
            messages.success(request, f"Course '{course.title}' was updated successfully!")
            return redirect('backend:courses_list')
    else:
        form = CourseForm(instance=course)

    return render(request, 'backend/course_form.html', {'form': form, 'course': course, 'title': f'Edit Course: {course.title}'})


@user_passes_test(is_admin_user, login_url='backend:admin_login')
def course_delete(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not request.user.is_superuser and course.instructor != request.user:
        messages.error(request, "Permission denied. You can only delete your own courses.")
        return redirect('backend:courses_list')

    if request.method == 'POST':
        title = course.title
        course.delete()
        messages.success(request, f"Course '{title}' was deleted.")
        return redirect('backend:courses_list')
    return render(request, 'backend/confirm_delete.html', {
        'object_name': f"Course: {course.title}",
        'cancel_url': 'backend:courses_list',
    })


# Lesson Management
@user_passes_test(is_admin_user, login_url='backend:admin_login')
def course_lessons(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not request.user.is_superuser and course.instructor != request.user:
        messages.error(request, "Permission denied. You can only manage lessons for your own courses.")
        return redirect('backend:courses_list')

    lessons = course.lessons.all().order_by('order', 'id')
    return render(request, 'backend/lessons_list.html', {
        'course': course,
        'lessons': lessons,
    })


@user_passes_test(is_admin_user, login_url='backend:admin_login')
def lesson_create(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not request.user.is_superuser and course.instructor != request.user:
        messages.error(request, "Permission denied. You can only add lessons to your own courses.")
        return redirect('backend:courses_list')

    next_order = course.lessons.count() + 1
    if request.method == 'POST':
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            lesson.save()
            messages.success(request, f"Lesson '{lesson.title}' was added successfully to {course.title}.")
            return redirect('backend:course_lessons', course_id=course.id)
    else:
        form = LessonForm(initial={'order': next_order})

    return render(request, 'backend/lesson_form.html', {
        'form': form,
        'course': course,
        'title': f"Add Lesson to {course.title}",
    })


@user_passes_test(is_admin_user, login_url='backend:admin_login')
def lesson_edit(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.course
    if not request.user.is_superuser and course.instructor != request.user:
        messages.error(request, "Permission denied. You can only edit lessons for your own courses.")
        return redirect('backend:courses_list')

    if request.method == 'POST':
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, f"Lesson '{lesson.title}' was updated successfully.")
            return redirect('backend:course_lessons', course_id=course.id)
    else:
        form = LessonForm(instance=lesson)

    return render(request, 'backend/lesson_form.html', {
        'form': form,
        'course': course,
        'lesson': lesson,
        'title': f"Edit Lesson: {lesson.title}",
    })


@user_passes_test(is_admin_user, login_url='backend:admin_login')
def lesson_delete(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.course
    if not request.user.is_superuser and course.instructor != request.user:
        messages.error(request, "Permission denied. You can only delete lessons from your own courses.")
        return redirect('backend:courses_list')

    course_id = course.id
    if request.method == 'POST':
        title = lesson.title
        lesson.delete()
        messages.success(request, f"Lesson '{title}' was deleted.")
        return redirect('backend:course_lessons', course_id=course_id)
    return render(request, 'backend/confirm_delete.html', {
        'object_name': f"Lesson: {lesson.title} ({course.title})",
        'cancel_url': 'backend:course_lessons',
        'cancel_args': [course_id],
    })


# Category Management
@user_passes_test(is_admin_user, login_url='backend:admin_login')
def categories_list(request):
    categories = Category.objects.annotate(course_count=Count('courses')).order_by('name')
    return render(request, 'backend/categories_list.html', {'categories': categories})


@user_passes_test(is_superuser, login_url='backend:admin_login')
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' was created successfully!")
            return redirect('backend:categories_list')
    else:
        form = CategoryForm()
    return render(request, 'backend/category_form.html', {'form': form, 'title': 'Create New Category'})


@user_passes_test(is_superuser, login_url='backend:admin_login')
def category_edit(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' was updated successfully!")
            return redirect('backend:categories_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'backend/category_form.html', {'form': form, 'category': category, 'title': f"Edit Category: {category.name}"})


@user_passes_test(is_superuser, login_url='backend:admin_login')
def category_delete(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f"Category '{name}' was deleted.")
        return redirect('backend:categories_list')
    return render(request, 'backend/confirm_delete.html', {
        'object_name': f"Category: {category.name}",
        'cancel_url': 'backend:categories_list',
    })


# Enrollment Management
@user_passes_test(is_admin_user, login_url='backend:admin_login')
def enrollments_list(request):
    status_filter = request.GET.get('status', '').strip()
    enrollments = Enrollment.objects.select_related('user', 'course').order_by('-enrolled_at')

    if not request.user.is_superuser:
        enrollments = enrollments.filter(course__instructor=request.user)

    if status_filter:
        enrollments = enrollments.filter(status=status_filter)

    context = {
        'enrollments': enrollments,
        'status_filter': status_filter,
        'total_count': enrollments.count(),
        'is_instructor': not request.user.is_superuser,
    }
    return render(request, 'backend/enrollments_list.html', context)


@user_passes_test(is_admin_user, login_url='backend:admin_login')
def enrollment_detail(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment.objects.select_related('user', 'course'), id=enrollment_id)
    if not request.user.is_superuser and enrollment.course.instructor != request.user:
        messages.error(request, "Permission denied. You can only view learning progress for your own courses.")
        return redirect('backend:enrollments_list')

    course = enrollment.course
    student = enrollment.user
    lessons = course.lessons.all().order_by('order', 'id')
    progress_records = {
        lp.lesson_id: lp
        for lp in LessonProgress.objects.filter(student=student, lesson__course=course)
    }

    lessons_with_status = []
    for lesson in lessons:
        rec = progress_records.get(lesson.id)
        lessons_with_status.append({
            'lesson': lesson,
            'is_completed': rec.is_completed if rec else False,
            'completed_at': rec.completed_at if rec else None,
        })

    context = {
        'enrollment': enrollment,
        'student': student,
        'course': course,
        'lessons_with_status': lessons_with_status,
    }
    return render(request, 'backend/enrollment_detail.html', context)


@user_passes_test(is_admin_user, login_url='backend:admin_login')
def enrollment_update_status(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    if not request.user.is_superuser and enrollment.course.instructor != request.user:
        messages.error(request, "Permission denied.")
        return redirect('backend:enrollments_list')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Enrollment.STATUS_CHOICES):
            enrollment.status = new_status
            if new_status == 'Completed':
                enrollment.progress = 100
            enrollment.save()
            messages.success(request, f"Enrollment for {enrollment.user.username} updated to '{new_status}'.")
    return redirect('backend:enrollments_list')


# Instructor Management (Superuser Only)
@user_passes_test(is_superuser, login_url='backend:admin_login')
def instructors_list(request):
    instructors = User.objects.filter(is_staff=True).annotate(
        course_count=Count('instructed_courses')
    ).order_by('-date_joined')

    query = request.GET.get('q', '').strip()
    if query:
        instructors = instructors.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )

    context = {
        'instructors': instructors,
        'query': query,
        'total_count': instructors.count(),
    }
    return render(request, 'backend/instructors_list.html', context)


@user_passes_test(is_superuser, login_url='backend:admin_login')
def instructor_create(request):
    if request.method == 'POST':
        form = InstructorForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                is_staff=True,
            )
            messages.success(request, f"Instructor account for {user.get_full_name() or user.username} was created successfully!")
            return redirect('backend:instructors_list')
    else:
        form = InstructorForm()

    return render(request, 'backend/instructor_form.html', {
        'form': form,
        'title': 'Create Instructor Account'
    })


@user_passes_test(is_superuser, login_url='backend:admin_login')
def instructor_toggle_status(request, user_id):
    instructor = get_object_or_404(User, id=user_id, is_staff=True)
    if instructor.id == request.user.id:
        messages.error(request, "You cannot deactivate your own administrative account.")
        return redirect('backend:instructors_list')
    instructor.is_active = not instructor.is_active
    instructor.save()
    status_str = "activated" if instructor.is_active else "suspended"
    messages.success(request, f"Instructor account '{instructor.username}' has been {status_str}.")
    return redirect('backend:instructors_list')


# Reviews Management
@user_passes_test(is_admin_user, login_url='backend:admin_login')
def reviews_list(request):
    course_id = request.GET.get('course', '').strip()
    rating_filter = request.GET.get('rating', '').strip()

    reviews = CourseReview.objects.select_related('course', 'student').order_by('-created_at')

    if not request.user.is_superuser:
        reviews = reviews.filter(course__instructor=request.user)

    if course_id:
        reviews = reviews.filter(course_id=course_id)

    if rating_filter:
        reviews = reviews.filter(rating=rating_filter)

    courses = Course.objects.all() if request.user.is_superuser else Course.objects.filter(instructor=request.user)

    context = {
        'reviews': reviews,
        'courses': courses,
        'selected_course': course_id,
        'selected_rating': rating_filter,
        'total_count': reviews.count(),
        'is_instructor': not request.user.is_superuser,
    }
    return render(request, 'backend/reviews_list.html', context)


@user_passes_test(is_admin_user, login_url='backend:admin_login')
def review_delete(request, review_id):
    review = get_object_or_404(CourseReview, id=review_id)
    if not request.user.is_superuser and review.course.instructor != request.user:
        messages.error(request, "Permission denied. You can only delete reviews for your own courses.")
        return redirect('backend:reviews_list')

    if request.method == 'POST':
        course_title = review.course.title
        student_name = review.student.username
        review.delete()
        messages.success(request, f"Review by @{student_name} on '{course_title}' was deleted.")
        return redirect('backend:reviews_list')

    return render(request, 'backend/confirm_delete.html', {
        'object_name': f"Review by @{review.student.username} on '{review.course.title}'",
        'cancel_url': 'backend:reviews_list',
    })


# Contact Inquiries
@user_passes_test(is_admin_user, login_url='backend:admin_login')
def messages_list(request):
    filter_type = request.GET.get('filter', '').strip()
    inquiries = ContactMessage.objects.all().order_by('-created_at')

    if filter_type == 'unread':
        inquiries = inquiries.filter(is_read=False)
    elif filter_type == 'read':
        inquiries = inquiries.filter(is_read=True)

    context = {
        'inquiries': inquiries,
        'filter_type': filter_type,
        'unread_count': ContactMessage.objects.filter(is_read=False).count(),
    }
    return render(request, 'backend/messages_list.html', context)


@user_passes_test(is_admin_user, login_url='backend:admin_login')
def message_toggle_read(request, message_id):
    inquiry = get_object_or_404(ContactMessage, id=message_id)
    inquiry.is_read = not inquiry.is_read
    inquiry.save()
    status_str = "read" if inquiry.is_read else "unread"
    messages.info(request, f"Message from {inquiry.name} marked as {status_str}.")
    return redirect('backend:messages_list')


@user_passes_test(is_admin_user, login_url='backend:admin_login')
def message_delete(request, message_id):
    inquiry = get_object_or_404(ContactMessage, id=message_id)
    if request.method == 'POST':
        name = inquiry.name
        inquiry.delete()
        messages.success(request, f"Inquiry from {name} deleted.")
        return redirect('backend:messages_list')
    return render(request, 'backend/confirm_delete.html', {
        'object_name': f"Inquiry from {inquiry.name} ({inquiry.email})",
        'cancel_url': 'backend:messages_list',
    })
