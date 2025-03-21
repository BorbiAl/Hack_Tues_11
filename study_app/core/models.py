from django.db import models
import bcrypt
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone

class AuthUser(AbstractUser):
    groups = models.ManyToManyField(
        Group,
        related_name='authuser_set', 
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='authuser_permissions_set', 
        blank=True,
    )
    created_at = models.DateTimeField(default=timezone.now)

class User(models.Model):
    username = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=255)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, password):
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

class Subject(models.Model):
    name = models.CharField(max_length=255) 
    description = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.name

class Test(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='tests') 
    title = models.CharField(max_length=255, default='No title available') 
    questions = models.TextField(default='No questions available') 
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title