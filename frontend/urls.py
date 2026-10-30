from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'frontend'

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('courses/', views.courses, name='courses'),
    path('courses/detail/', views.course_detail_fallback, name='course_detail_default'),
    path('courses/<slug:slug>/', views.course_detail, name='course_detail'),
    path('courses/<slug:slug>/enroll/', views.enroll_course, name='enroll_course'),
    path('courses/<slug:slug>/review/', views.add_course_review, name='add_course_review'),
    path('courses/<slug:slug>/learn/', views.lesson_learning, name='course_learn'),
    path('courses/<slug:slug>/learn/<int:lesson_id>/', views.lesson_learning, name='lesson_learning'),
    path('courses/<slug:slug>/lessons/<int:lesson_id>/complete/', views.toggle_lesson_completion, name='toggle_lesson_completion'),
    
    path('blog/', views.blog, name='blog'),
    path('blog/single/', views.blog_single, name='blog_single'),
    path('contact/', views.contact, name='contact'),
    
    # Student Authentication & Dashboard
    path('login/', views.student_login, name='login'),
    path('register/', views.student_register, name='register'),
    path('logout/', views.student_logout, name='logout'),
    path('dashboard/', views.student_dashboard, name='dashboard'),
    path('profile/update/', views.student_profile_update, name='profile_update'),
    path('password/change/', views.student_password_change, name='password_change'),
    
    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='frontend/password_reset.html',
        email_template_name='frontend/password_reset_email.html',
        subject_template_name='frontend/password_reset_subject.txt',
        success_url=reverse_lazy('frontend:password_reset_done')
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='frontend/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='frontend/password_reset_confirm.html',
        success_url=reverse_lazy('frontend:password_reset_complete')
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='frontend/password_reset_complete.html'
    ), name='password_reset_complete'),
]

