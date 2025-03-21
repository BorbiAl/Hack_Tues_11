from django.db import models
from django.contrib.auth.models import AbstractUser
import bcrypt

class User(models.Model):
    username = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=255)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, password):
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

class Subject(models.Model):
    name = models.CharField(max_length=255)  # Subject name (e.g., Math, Science)
    description = models.TextField(blank=True, null=True)  # Optional description

    def __str__(self):
        return self.name

class Test(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='tests')  # Link to subject
    title = models.CharField(max_length=255)  # Test title
    questions = models.TextField()  # Store questions as JSON or plain text
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for creation

    def __str__(self):
        return self.title