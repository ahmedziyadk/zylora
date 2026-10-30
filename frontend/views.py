from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Avg
from django.utils import timezone

from backend.models import Category, Course, Enrollment, Lesson, LessonProgress, CourseReview, ContactMessage
from .forms import StudentLoginForm, StudentRegisterForm, StudentProfileUpdateForm, CourseReviewForm, StudentPasswordChangeForm
from .models import StudentProfile


def index(request):
    featured_courses = Course.objects.filter(is_published=True).select_related('category').order_by('-is_featured', '-created_at')[:6]
    categories = Category.objects.annotate(
        course_count=Count('courses', filter=Q(courses__is_published=True))
    ).order_by('name')

    total_courses = Course.objects.filter(is_published=True).count()
    total_students = User.objects.filter(is_staff=False).count()
    total_categories = categories.count()
    total_lessons = Lesson.objects.filter(course__is_published=True).count()

    context = {
        'featured_courses': featured_courses,
        'categories': categories,
        'total_courses': total_courses,
        'total_students': total_students,
        'total_categories': total_categories,
        'total_lessons': total_lessons,
    }
    return render(request, 'frontend/index.html', context)


def about(request):
    total_courses = Course.objects.filter(is_published=True).count()
    total_students = User.objects.filter(is_staff=False).count()
    categories = Category.objects.annotate(
        course_count=Count('courses', filter=Q(courses__is_published=True))
    ).order_by('name')

    return render(request, 'frontend/about.html', {
        'total_courses': total_courses,
        'total_students': total_students,
        'categories': categories,
    })


def courses(request):
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '').strip()
    level = request.GET.get('level', '').strip()
    price_type = (request.GET.get('price_type') or request.GET.get('price', '')).strip()

    courses_qs = Course.objects.filter(is_published=True).select_related('category').order_by('-created_at')

    if query:
        courses_qs = courses_qs.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(instructor_name__icontains=query)
        )

    if category_slug:
        if category_slug.isdigit():
            courses_qs = courses_qs.filter(category_id=category_slug)
        else:
            courses_qs = courses_qs.filter(category__slug=category_slug)

    if level:
        courses_qs = courses_qs.filter(level__iexact=level)

    if price_type == 'free':
        courses_qs = courses_qs.filter(price=0)
    elif price_type == 'paid':
        courses_qs = courses_qs.filter(price__gt=0)

    # Categories sidebar with dynamic counts
    categories = Category.objects.annotate(
        course_count=Count('courses', filter=Q(courses__is_published=True))
    ).order_by('name')

    # Latest 3 courses for sidebar
    latest_courses = Course.objects.filter(is_published=True).order_by('-created_at')[:3]

    # Pagination: 6 courses per page
    paginator = Paginator(courses_qs, 6)
    page_number = request.GET.get('page')
    courses_page = paginator.get_page(page_number)

    context = {
        'courses': courses_page,
        'categories': categories,
        'latest_courses': latest_courses,
        'query': query,
        'selected_category': category_slug,
        'selected_level': level,
        'selected_price': price_type,
        'total_count': courses_qs.count(),
    }
    return render(request, 'frontend/courses.html', context)


def course_detail_fallback(request):
    first_course = Course.objects.filter(is_published=True).first()
    if first_course:
        return redirect('frontend:course_detail', slug=first_course.slug)
    messages.info(request, "No courses are currently available.")
    return redirect('frontend:courses')


def course_detail(request, slug=None):
    if not slug:
        return course_detail_fallback(request)

    course = get_object_or_404(Course, slug=slug, is_published=True)
    lessons = course.lessons.all().order_by('order', 'id')
    reviews = course.reviews.select_related('student').order_by('-created_at')

    avg_rating_val = reviews.aggregate(Avg('rating'))['rating__avg'] or 5.0
    avg_rating = round(avg_rating_val, 1)

    is_enrolled = False
    enrollment = None
    completed_lesson_ids = set()

    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
        is_enrolled = enrollment is not None
        if is_enrolled:
            completed_lesson_ids = set(
                LessonProgress.objects.filter(
                    student=request.user,
                    lesson__course=course,
                    is_completed=True
                ).values_list('lesson_id', flat=True)
            )

    latest_courses = Course.objects.filter(is_published=True).exclude(id=course.id).order_by('-created_at')[:3]
    first_lesson = lessons.first()

    context = {
        'course': course,
        'lessons': lessons,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'rating_int': int(avg_rating),
        'is_enrolled': is_enrolled,
        'enrollment': enrollment,
        'completed_lesson_ids': completed_lesson_ids,
        'latest_courses': latest_courses,
        'first_lesson': first_lesson,
    }
    return render(request, 'frontend/course.html', context)


@login_required(login_url='frontend:login')
def enroll_course(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)
    if request.method == 'POST':
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course,
            defaults={'status': 'Active', 'progress': 0}
        )
        if created:
            messages.success(request, f"Welcome to '{course.title}'! You are now successfully enrolled.")
        else:
            messages.info(request, f"You are already enrolled in '{course.title}'.")

        first_lesson = course.lessons.order_by('order').first()
        if first_lesson:
            return redirect('frontend:lesson_learning', slug=course.slug, lesson_id=first_lesson.id)
        return redirect('frontend:course_detail', slug=course.slug)

    return redirect('frontend:course_detail', slug=course.slug)


def lesson_learning(request, slug, lesson_id=None):
    course = get_object_or_404(Course, slug=slug, is_published=True)
    lessons = course.lessons.all().order_by('order', 'id')

    if not lessons.exists():
        messages.warning(request, "No lessons have been published for this course yet.")
        return redirect('frontend:course_detail', slug=course.slug)

    if lesson_id:
        lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    else:
        lesson = lessons.first()

    # Authorization verification
    if not lesson.is_preview:
        if not request.user.is_authenticated:
            messages.info(request, "Please log in to access this lesson.")
            return redirect(f"{reverse('frontend:login')}?next={request.path}")

        is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
        is_staff_or_instructor = request.user.is_staff or (course.instructor == request.user)
        if not is_enrolled and not is_staff_or_instructor:
            messages.error(request, "You must enroll in this course to access this lesson.")
            return redirect('frontend:course_detail', slug=course.slug)
    else:
        is_enrolled = request.user.is_authenticated and Enrollment.objects.filter(user=request.user, course=course).exists()

    enrollment = None
    completed_lesson_ids = set()
    if request.user.is_authenticated and is_enrolled:
        enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
        completed_lesson_ids = set(
            LessonProgress.objects.filter(
                student=request.user,
                lesson__course=course,
                is_completed=True
            ).values_list('lesson_id', flat=True)
        )

    is_completed = lesson.id in completed_lesson_ids

    # Find previous and next lessons
    lesson_list = list(lessons)
    curr_index = lesson_list.index(lesson)
    prev_lesson = lesson_list[curr_index - 1] if curr_index > 0 else None
    next_lesson = lesson_list[curr_index + 1] if curr_index < len(lesson_list) - 1 else None

    context = {
        'course': course,
        'lesson': lesson,
        'lessons': lessons,
        'enrollment': enrollment,
        'completed_lesson_ids': completed_lesson_ids,
        'is_completed': is_completed,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'is_enrolled': is_enrolled,
    }
    return render(request, 'frontend/lesson_detail.html', context)


@login_required(login_url='frontend:login')
def toggle_lesson_completion(request, slug, lesson_id):
    course = get_object_or_404(Course, slug=slug, is_published=True)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    enrollment, _ = Enrollment.objects.get_or_create(user=request.user, course=course)

    progress_obj, created = LessonProgress.objects.get_or_create(student=request.user, lesson=lesson)

    if progress_obj.is_completed:
        progress_obj.is_completed = False
        progress_obj.completed_at = None
        progress_obj.save()
        messages.info(request, f"Lesson '{lesson.title}' marked as incomplete.")
        enrollment.recalculate_progress()
        return redirect('frontend:lesson_learning', slug=course.slug, lesson_id=lesson.id)
    else:
        progress_obj.is_completed = True
        progress_obj.completed_at = timezone.now()
        progress_obj.save()
        new_pct = enrollment.recalculate_progress()
        messages.success(request, f"Lesson '{lesson.title}' marked complete! Progress: {new_pct}%")

        # Auto-advance to next lesson if available
        next_lesson = course.lessons.filter(order__gt=lesson.order).order_by('order').first()
        if next_lesson:
            return redirect('frontend:lesson_learning', slug=course.slug, lesson_id=next_lesson.id)
        return redirect('frontend:lesson_learning', slug=course.slug, lesson_id=lesson.id)


@login_required(login_url='frontend:login')
def add_course_review(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)
    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()

    if not is_enrolled:
        messages.error(request, "Only enrolled students can write reviews for this course.")
        return redirect('frontend:course_detail', slug=course.slug)

    if request.method == 'POST':
        form = CourseReviewForm(request.POST)
        if form.is_valid():
            rating = int(form.cleaned_data['rating'])
            comment = form.cleaned_data['comment'].strip()
            CourseReview.objects.update_or_create(
                course=course,
                student=request.user,
                defaults={'rating': rating, 'comment': comment}
            )
            messages.success(request, "Thank you! Your course review has been saved.")
        else:
            messages.error(request, "Please provide a valid rating and review text.")

    return redirect('frontend:course_detail', slug=course.slug)


def blog(request):
    return render(request, 'frontend/blog.html')


def blog_single(request):
    return render(request, 'frontend/blog_single.html')


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', 'General Inquiry').strip()
        message_text = request.POST.get('message', '').strip()

        if name and email and message_text:
            ContactMessage.objects.create(name=name, email=email, subject=subject, message=message_text)
            messages.success(request, "Thank you! Your message has been sent to the Zylora team successfully.")
            return redirect('frontend:contact')
        else:
            messages.error(request, "Please fill in all required fields (Name, Email, Message).")

    return render(request, 'frontend/contact.html')


def student_login(request):
    # Role-based redirect if already authenticated
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('backend:dashboard')
        if request.GET.get('next') and '/admin' in request.GET.get('next'):
            messages.error(request, "Access denied. Administrator privileges required.")
        return redirect('frontend:dashboard')

    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            login_input = form.cleaned_data['username'].strip()
            password = form.cleaned_data['password']

            # Authenticate by username
            user = authenticate(request, username=login_input, password=password)

            # If not matched, try authenticating by email
            if user is None and '@' in login_input:
                try:
                    user_obj = User.objects.get(email__iexact=login_input)
                    user = authenticate(request, username=user_obj.username, password=password)
                except (User.DoesNotExist, User.MultipleObjectsReturned):
                    user = None

            # Check if this is an inactive account with matching credentials
            if user is None:
                inactive_user = None
                try:
                    if '@' in login_input:
                        inactive_user = User.objects.get(email__iexact=login_input, is_active=False)
                    else:
                        inactive_user = User.objects.get(username__iexact=login_input, is_active=False)
                except (User.DoesNotExist, User.MultipleObjectsReturned):
                    inactive_user = None

                if inactive_user and inactive_user.check_password(password):
                    messages.error(request, "This account is currently inactive. Please contact support.")
                    return render(request, 'frontend/login.html', {'form': form})

            if user is not None:
                if not user.is_active:
                    messages.error(request, "This account is currently inactive. Please contact support.")
                    return render(request, 'frontend/login.html', {'form': form})

                login(request, user)
                display_name = user.first_name or user.username

                # Evaluate next URL redirect safely
                next_url = request.GET.get('next') or request.POST.get('next')

                # Role-based redirect
                if user.is_staff or user.is_superuser:
                    messages.success(request, f"Welcome back, {display_name}! Signed in to administrative management.")
                    if next_url and next_url.startswith('/'):
                        return redirect(next_url)
                    return redirect('backend:dashboard')
                else:
                    messages.success(request, f"Welcome back, {display_name}!")
                    # Protect against students being redirected to administrative URLs via next parameter
                    if next_url and next_url.startswith('/') and not next_url.startswith('/admin'):
                        return redirect(next_url)
                    return redirect('frontend:dashboard')
            else:
                messages.error(request, "Invalid username/email or password. Please try again.")
    else:
        form = StudentLoginForm()

    return render(request, 'frontend/login.html', {'form': form})


# Semantic alias
unified_login = student_login


def student_register(request):
    # Role-based redirect if already authenticated
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('backend:dashboard')
        return redirect('frontend:dashboard')

    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            # Automatically create public registration as student only
            # Explicitly enforce is_staff=False and is_superuser=False to prevent privilege escalation
            first_name = form.cleaned_data.get('first_name', '').strip()
            last_name = form.cleaned_data.get('last_name', '').strip()

            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=first_name,
                last_name=last_name,
            )
            user.is_staff = False
            user.is_superuser = False
            user.save()

            phone = form.cleaned_data.get('phone', '')
            StudentProfile.objects.create(user=user, phone=phone)

            login(request, user)
            display_name = user.get_full_name() or user.username
            messages.success(request, f"Welcome to Zylora, {display_name}! Your student account is now active.")
            return redirect('frontend:dashboard')
        else:
            messages.error(request, "Please correct the errors below to complete your registration.")
    else:
        form = StudentRegisterForm()

    return render(request, 'frontend/register.html', {'form': form})


def student_logout(request):
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "You have been logged out successfully.")
    return redirect('frontend:index')


@login_required(login_url='frontend:login')
def student_dashboard(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    enrollments = Enrollment.objects.filter(user=request.user).select_related('course', 'course__category').order_by('-enrolled_at')

    total_enrolled = enrollments.count()
    completed_count = enrollments.filter(status='Completed').count()
    in_progress_count = enrollments.filter(status='Active').count()
    total_completed_lessons = LessonProgress.objects.filter(student=request.user, is_completed=True).count()

    password_form = StudentPasswordChangeForm(user=request.user)

    context = {
        'profile': profile,
        'enrollments': enrollments,
        'total_enrolled': total_enrolled,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'total_completed_lessons': total_completed_lessons,
        'password_form': password_form,
    }
    return render(request, 'frontend/dashboard.html', context)


@login_required(login_url='frontend:login')
def student_profile_update(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = StudentProfileUpdateForm(request.POST)
        if form.is_valid():
            user = request.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            new_email = form.cleaned_data['email'].strip().lower()

            # Ensure email uniqueness among other accounts
            if User.objects.filter(email__iexact=new_email).exclude(id=user.id).exists():
                messages.error(request, "This email address is already in use by another account.")
                return redirect('frontend:dashboard')

            user.email = new_email
            user.save()

            profile.phone = form.cleaned_data.get('phone', '')
            profile.headline = form.cleaned_data.get('headline', '')
            profile.bio = form.cleaned_data.get('bio', '')
            profile.save()

            messages.success(request, "Your profile details have been updated successfully.")
            return redirect('frontend:dashboard')
    return redirect('frontend:dashboard')


@login_required(login_url='frontend:login')
def student_password_change(request):
    if request.method == 'POST':
        form = StudentPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Your password has been changed successfully.")
            return redirect('frontend:dashboard')
        else:
            for error_list in form.errors.values():
                for err in error_list:
                    messages.error(request, err)
    return redirect('frontend:dashboard')




