from django.contrib import admin
from .models import Category, Course, Lesson, Enrollment, LessonProgress, CourseReview, ContactMessage

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ('order', 'title', 'duration_minutes', 'is_preview', 'video_url')
    ordering = ('order',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'instructor_name', 'price', 'duration_weeks', 'level', 'is_featured', 'is_published', 'created_at')
    list_filter = ('category', 'level', 'is_featured', 'is_published', 'created_at')
    search_fields = ('title', 'instructor_name', 'description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [LessonInline]
    actions = ['publish_courses', 'unpublish_courses', 'feature_courses']

    @admin.action(description='Publish selected courses')
    def publish_courses(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description='Unpublish selected courses')
    def unpublish_courses(self, request, queryset):
        queryset.update(is_published=False)

    @admin.action(description='Mark selected courses as Featured')
    def feature_courses(self, request, queryset):
        queryset.update(is_featured=True)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'duration_minutes', 'is_preview', 'created_at')
    list_filter = ('course', 'is_preview', 'created_at')
    search_fields = ('title', 'content', 'course__title')
    ordering = ('course', 'order')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'progress', 'status', 'enrolled_at')
    list_filter = ('status', 'enrolled_at')
    search_fields = ('user__username', 'user__email', 'course__title')
    actions = ['mark_as_completed', 'recalculate_selected_progress']

    @admin.action(description='Mark enrollment as Completed')
    def mark_as_completed(self, request, queryset):
        queryset.update(status='Completed', progress=100)

    @admin.action(description='Recalculate progress for selected enrollments')
    def recalculate_selected_progress(self, request, queryset):
        for e in queryset:
            e.recalculate_progress()


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'is_completed', 'completed_at')
    list_filter = ('is_completed', 'completed_at')
    search_fields = ('student__username', 'lesson__title', 'lesson__course__title')


@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = ('course', 'student', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('course__title', 'student__username', 'comment')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    actions = ['mark_as_read', 'mark_as_unread']

    @admin.action(description='Mark selected messages as Read')
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description='Mark selected messages as Unread')
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
