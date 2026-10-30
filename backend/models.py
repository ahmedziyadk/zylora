from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.templatetags.static import static

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon = models.CharField(max_length=50, default='fa-laptop', help_text='Font Awesome class name')
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Course Category'
        verbose_name_plural = 'Course Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Course(models.Model):
    LEVEL_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    instructor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='instructed_courses')
    instructor_name = models.CharField(max_length=150, default='Zylora Faculty')
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    image = models.ImageField(upload_to='courses/', blank=True, null=True)
    description = models.TextField()
    duration_weeks = models.PositiveIntegerField(default=8, help_text='Course duration in weeks')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='Beginner')
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or 'course'
            slug = base_slug
            counter = 1
            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        if self.instructor and (not self.instructor_name or self.instructor_name == 'Zylora Faculty'):
            self.instructor_name = self.instructor.get_full_name() or self.instructor.username
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def is_free(self):
        return self.price == 0

    @property
    def total_lessons(self):
        return self.lessons.count()

    @property
    def total_students(self):
        return self.enrollments.count()

    def get_thumbnail_url(self):
        if self.image:
            return self.image.url
        idx = ((self.id or 1) % 9) + 1
        return static(f'frontend/images/course_{idx}.jpg')


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)
    content = models.TextField(blank=True, help_text='Lesson notes, curriculum details, or learning materials')
    video_url = models.CharField(max_length=300, blank=True, help_text='Video URL (YouTube, Vimeo, MP4, etc.)')
    duration_minutes = models.PositiveIntegerField(default=15, help_text='Estimated duration in minutes')
    is_preview = models.BooleanField(default=False, help_text='Allow free preview before enrollment')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        unique_together = ('course', 'order')

    def __str__(self):
        return f"{self.course.title} - L{self.order}: {self.title}"


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Completed', 'Completed'),
        ('Dropped', 'Dropped'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    progress = models.PositiveIntegerField(default=0, help_text='Progress percentage from 0 to 100')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.user.username} - {self.course.title} ({self.status})"

    def recalculate_progress(self):
        total_lessons = self.course.lessons.count()
        if total_lessons == 0:
            return self.progress
        completed_lessons = LessonProgress.objects.filter(
            student=self.user,
            lesson__course=self.course,
            is_completed=True
        ).count()
        new_progress = int(min(100, round((completed_lessons / total_lessons) * 100)))
        self.progress = new_progress
        if new_progress == 100:
            self.status = 'Completed'
        elif self.status == 'Completed' and new_progress < 100:
            self.status = 'Active'
        self.save(update_fields=['progress', 'status', 'updated_at'])
        return new_progress


class LessonProgress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='student_progress')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('student', 'lesson')
        verbose_name = 'Lesson Progress'
        verbose_name_plural = 'Lesson Progress Records'

    def __str__(self):
        status = "Completed" if self.is_completed else "Incomplete"
        return f"{self.student.username} - {self.lesson.title} ({status})"


class CourseReview(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_reviews')
    rating = models.PositiveIntegerField(default=5, help_text='Rating from 1 to 5 stars')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('course', 'student')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.course.title} - {self.student.username} ({self.rating}*)"


class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=250, blank=True, default='General Inquiry')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Inquiry from {self.name} ({self.email})"

