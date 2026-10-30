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

    def get_embed_video_url(self):
        """
        Safely converts YouTube (watch, short, shorts, embed), Vimeo,
        and Dailymotion URLs into valid, embeddable iframe URLs.
        Returns empty string if direct video or unsupported.
        """
        if not self.video_url:
            return ""
        
        raw_url = self.video_url.strip()
        if not raw_url:
            return ""

        from urllib.parse import urlparse, parse_qs

        # Direct video files are handled separately via HTML5 video tag
        clean_lower = raw_url.lower().split('?')[0]
        if clean_lower.endswith(('.mp4', '.webm', '.ogg', '.mov', '.m4v', '.m3u8')):
            return ""

        # YouTube Watch URL: https://www.youtube.com/watch?v=VIDEO_ID
        if 'youtube.com/watch' in raw_url:
            try:
                parsed = urlparse(raw_url)
                params = parse_qs(parsed.query)
                video_id = params.get('v')
                if video_id and video_id[0]:
                    return f"https://www.youtube.com/embed/{video_id[0]}"
            except Exception:
                pass

        # YouTube Short URL: https://youtu.be/VIDEO_ID or https://youtu.be/VIDEO_ID?si=...
        elif 'youtu.be/' in raw_url:
            try:
                parsed = urlparse(raw_url)
                video_id = parsed.path.strip('/')
                if video_id:
                    return f"https://www.youtube.com/embed/{video_id}"
            except Exception:
                pass

        # YouTube Shorts: https://www.youtube.com/shorts/VIDEO_ID
        elif 'youtube.com/shorts/' in raw_url:
            try:
                parsed = urlparse(raw_url)
                parts = parsed.path.split('/shorts/')
                if len(parts) > 1:
                    video_id = parts[1].strip('/')
                    if video_id:
                        return f"https://www.youtube.com/embed/{video_id}"
            except Exception:
                pass

        # Already YouTube embed: https://www.youtube.com/embed/VIDEO_ID
        elif 'youtube.com/embed/' in raw_url or 'youtube-nocookie.com/embed/' in raw_url:
            return raw_url

        # Vimeo Standard: https://vimeo.com/123456789
        elif 'vimeo.com/' in raw_url and 'player.vimeo.com' not in raw_url:
            try:
                parsed = urlparse(raw_url)
                vimeo_id = parsed.path.strip('/')
                if vimeo_id.isdigit():
                    return f"https://player.vimeo.com/video/{vimeo_id}"
            except Exception:
                pass

        # Already Vimeo embed: https://player.vimeo.com/video/123456789
        elif 'player.vimeo.com/video/' in raw_url:
            return raw_url

        # Dailymotion: https://dai.ly/x7tgad0 or https://www.dailymotion.com/video/x7tgad0
        elif 'dai.ly/' in raw_url:
            try:
                parsed = urlparse(raw_url)
                dm_id = parsed.path.strip('/')
                if dm_id:
                    return f"https://www.dailymotion.com/embed/video/{dm_id}"
            except Exception:
                pass
        elif 'dailymotion.com/video/' in raw_url:
            try:
                parsed = urlparse(raw_url)
                parts = parsed.path.split('/video/')
                if len(parts) > 1:
                    dm_id = parts[1].strip('/')
                    if dm_id:
                        return f"https://www.dailymotion.com/embed/video/{dm_id}"
            except Exception:
                pass

        # Any URL that is already formatted as an iframe embed endpoint
        elif '/embed/' in raw_url:
            return raw_url

        return ""

    @property
    def is_direct_video(self):
        """Returns True if the video_url points to a standard direct video file."""
        if not self.video_url:
            return False
        clean_url = self.video_url.strip().lower().split('?')[0]
        return clean_url.endswith(('.mp4', '.webm', '.ogg', '.mov', '.m4v', '.m3u8'))

    @property
    def embed_video_url(self):
        return self.get_embed_video_url()

    @property
    def has_valid_video(self):
        return bool(self.is_direct_video or self.embed_video_url)


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

