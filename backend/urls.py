from django.urls import path
from . import views

app_name = 'backend'

urlpatterns = [
    # Dashboard & Auth
    path('', views.dashboard_overview, name='dashboard'),
    path('login/', views.admin_login_view, name='admin_login'),
    path('logout/', views.admin_logout_view, name='admin_logout'),

    # Student Management
    path('students/', views.students_list, name='students_list'),
    path('students/<int:user_id>/toggle/', views.student_toggle_status, name='student_toggle_status'),
    path('students/<int:user_id>/delete/', views.student_delete, name='student_delete'),

    # Course Management
    path('courses/', views.courses_list, name='courses_list'),
    path('courses/create/', views.course_create, name='course_create'),
    path('courses/<int:course_id>/edit/', views.course_edit, name='course_edit'),
    path('courses/<int:course_id>/delete/', views.course_delete, name='course_delete'),

    # Lesson Management
    path('courses/<int:course_id>/lessons/', views.course_lessons, name='course_lessons'),
    path('courses/<int:course_id>/lessons/create/', views.lesson_create, name='lesson_create'),
    path('lessons/<int:lesson_id>/edit/', views.lesson_edit, name='lesson_edit'),
    path('lessons/<int:lesson_id>/delete/', views.lesson_delete, name='lesson_delete'),

    # Category Management
    path('categories/', views.categories_list, name='categories_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:category_id>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:category_id>/delete/', views.category_delete, name='category_delete'),

    # Instructor Management (Superuser)
    path('instructors/', views.instructors_list, name='instructors_list'),
    path('instructors/create/', views.instructor_create, name='instructor_create'),
    path('instructors/<int:user_id>/toggle/', views.instructor_toggle_status, name='instructor_toggle_status'),

    # Enrollment Management
    path('enrollments/', views.enrollments_list, name='enrollments_list'),
    path('enrollments/<int:enrollment_id>/detail/', views.enrollment_detail, name='enrollment_detail'),
    path('enrollments/<int:enrollment_id>/status/', views.enrollment_update_status, name='enrollment_update_status'),

    # Course Reviews Management
    path('reviews/', views.reviews_list, name='reviews_list'),
    path('reviews/<int:review_id>/delete/', views.review_delete, name='review_delete'),

    # Contact Inquiries
    path('messages/', views.messages_list, name='messages_list'),
    path('messages/<int:message_id>/toggle/', views.message_toggle_read, name='message_toggle_read'),
    path('messages/<int:message_id>/delete/', views.message_delete, name='message_delete'),
]

