from django.contrib import admin
from .models import StudentProfile

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_full_name', 'get_email', 'phone', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'phone')
    list_filter = ('created_at',)

    @admin.display(description='Full Name')
    def get_full_name(self, obj):
        return obj.user.get_full_name()

    @admin.display(description='Email')
    def get_email(self, obj):
        return obj.user.email

