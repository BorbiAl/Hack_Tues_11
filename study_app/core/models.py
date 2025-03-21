from django.db import models
import bcrypt
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

    
class User(AbstractUser):
    def check_password(self, password):
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    username = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=255)
    bio = models.TextField(blank=True, null=True)
    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    def __str__(self):
        return self.username


    

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