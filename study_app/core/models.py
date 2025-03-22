from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username field must be set")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username

class Subject(models.Model):
    name = models.CharField(max_length=255) 
    description = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.name

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


from django.db import models
from django.conf import settings

class Test(models.Model):
    title = models.CharField(max_length=255)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE, related_name='tests', blank=True, null=True)
    grade = models.IntegerField()  # Assuming grade is an integer
    question_data = models.TextField(default='')
    due_date = models.DateField(blank=True, null=True)

    def get_pdf_filename(self):
        # Generate the PDF filename based on subject and grade
        if self.subject and self.grade:
            return f"{self.subject.name.lower()}_{self.grade}.pdf"
        return None

class Question(models.Model):
    test = models.ForeignKey(Test, related_name='question_set', on_delete=models.CASCADE)  # Renamed related_name
    question_text = models.TextField()
    correct_answer = models.CharField(max_length=255)
    incorrect_answers = models.JSONField(default=list)

    def __str__(self):
        return self.question_text