from django.db import models
from django.contrib.auth.models import AbstractUser
import bcrypt
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .forms import SignupForm, LoginForm
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    
    pass

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
    title = models.CharField(max_length=255) 
    questions = models.TextField()  
    created_at = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return self.title
    
def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')  # Replace with your desired redirect
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})