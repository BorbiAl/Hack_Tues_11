from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm

def login_view(request):
    # Handle login logic here
    return render(request, 'core/login.html')

def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'core/signup.html', {'form': form})

def dashboard_view(request):
    return render(request, 'core/dashboard.html')

def profile_view(request):
    return render(request, 'core/profile.html')

def test_creation_view(request):
    return render(request, 'core/test_creation.html')

def test_list_view(request):
    return render(request, 'core/test_list.html')

def ranking_view(request):
    return render(request, 'core/ranking.html')