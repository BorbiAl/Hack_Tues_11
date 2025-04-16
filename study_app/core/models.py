from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

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


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    streak = models.IntegerField(default=0)
    last_test_date = models.DateField(null=True, blank=True) 

    def __str__(self):
        return f"{self.user.username}'s Profile"


class Subject(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Test(models.Model):
    title = models.CharField(max_length=255)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE, related_name='tests')
    grade = models.IntegerField()  # Grade (1 to 12)
    question_data = models.JSONField(default=list)  # Store questions as JSON
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set when the object is created

    def __str__(self):
        return self.title

class Question(models.Model):
    test = models.ForeignKey(Test, related_name='question_set', on_delete=models.CASCADE)  # Renamed related_name
    question_text = models.TextField()
    correct_answer = models.CharField(max_length=255)
    incorrect_answers = models.JSONField(default=list)

    def __str__(self):
        return self.question_text
    
class TestTextbook(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()

    def __str__(self):
        return self.title

class TestQuestion(models.Model):
    textbook = models.ForeignKey(TestTextbook, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()

    def __str__(self):
        return self.question_text

class Rag(models.Model):
    # Link each textbook with its corresponding Rag instance.
    textbook = models.OneToOneField(TestTextbook, on_delete=models.CASCADE, related_name='rag')
    # Additional fields related to the Rag model can be added here.

    def get_questions(self):
        # Retrieve questions via the textbook relationship.
        return self.textbook.questions.all()

    def __str__(self):
        return f"Rag for {self.textbook.title}"