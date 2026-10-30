from django import forms
from django.contrib.auth.models import User
from .models import Course, Category, Enrollment, Lesson

class AdminLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Admin Username or Email',
            'required': 'required',
            'autofocus': 'autofocus',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Admin Password',
            'required': 'required',
        })
    )


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'title', 'category', 'instructor', 'instructor_name', 'price',
            'duration_weeks', 'level', 'description', 'image', 'is_featured', 'is_published'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Course Title'}),
            'category': forms.Select(attrs={'class': 'form-control custom-select'}),
            'instructor': forms.Select(attrs={'class': 'form-control custom-select'}),
            'instructor_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Instructor Display Name'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '99.00', 'step': '0.01'}),
            'duration_weeks': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '8'}),
            'level': forms.Select(attrs={'class': 'form-control custom-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Detailed course overview and curriculum...'}),
            'image': forms.FileInput(attrs={'class': 'form-control-file'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'order', 'duration_minutes', 'is_preview', 'video_url', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lesson Title'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '15'}),
            'video_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'https://www.youtube.com/embed/...'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Lesson notes, learning objectives, resources...'}),
            'is_preview': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'icon', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category Name'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'category-slug (optional)'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fa-laptop'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Short description of this category...'}),
        }


class StudentEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    is_active = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']


class InstructorForm(forms.Form):
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name', 'required': 'required'})
    )
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name', 'required': 'required'})
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username', 'required': 'required'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'instructor@zylora.com', 'required': 'required'})
    )
    password = forms.CharField(
        min_length=6,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Initial Password (min 6 chars)', 'required': 'required'})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

