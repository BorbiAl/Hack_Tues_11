import openai
import pdfplumber
from langdetect import detect
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date
from django.contrib.auth import login
from core.models import Test, Subject
import json
from .forms import CustomUserCreationForm
from django.contrib.auth.views import LoginView
from .models import Profile
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.conf import settings
import os

openai.api_key = settings.OPENAI_API_KEY

def test_textbook_view(request):
    # Path to the media directory
    media_path = settings.MEDIA_ROOT
    files = []

    # Fetch all PDF files in the media directory
    for file_name in os.listdir(media_path):
        if file_name.endswith('.pdf'):
            files.append({
                'name': file_name,
                'url': f"{settings.MEDIA_URL}{file_name}"
            })

    return render(request, 'core/test_textbook.html', {'files': files})
def test_creation_view(request):

    if request.method == 'POST':
        # Get form data
        subject_name = request.POST.get('subject')
        grade = int(request.POST.get('grade'))
        start_page = int(request.POST.get('start_page'))
        end_page = int(request.POST.get('end_page'))
        pdf_url = request.POST.get('pdf_url')

        # Validate subject
        subject = Subject.objects.filter(name=subject_name).first()
        if not subject:
            subject = Subject.objects.create(name=subject_name)

        # Download and process the PDF
        pdf_path = os.path.join(settings.MEDIA_ROOT, os.path.basename(pdf_url))
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                if start_page < 1 or end_page > len(pdf.pages) or start_page > end_page:
                    raise ValueError("Invalid page range.")
                selected_text = ""
                for page_num in range(start_page - 1, end_page):
                    selected_text += pdf.pages[page_num].extract_text()
        except Exception as e:
            return render(request, 'core/test_creation.html', {
                'error': f"Error processing PDF: {str(e)}"
            })

        # Generate questions using OpenAI
        try:
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=f"Generate 10 multiple-choice questions with 4 options each (1 correct) based on the following text:\n\n{selected_text}",
                max_tokens=1500,
                temperature=0.7
            )
            questions = response.choices[0].text.strip()
        except Exception as e:
            return render(request, 'core/test_creation.html', {
                'error': f"Error generating questions: {str(e)}"
            })

        # Save the test
        test = Test.objects.create(
            title=f"{subject_name} Grade {grade} Test",
            subject=subject,
            grade=grade,
            question_data=questions
        )

        # Redirect to the test-taking page
        return redirect('take_test', test_id=test.id)

    return redirect('test_textbook')


def test_creation_view(request):
    if request.method == 'POST':
        # Get form data
        subject_name = request.POST.get('subject')
        grade = int(request.POST.get('grade'))
        start_page = int(request.POST.get('start_page'))
        end_page = int(request.POST.get('end_page'))
        pdf_url = request.POST.get('pdf_url')

        # Validate subject
        subject = Subject.objects.filter(name=subject_name).first()
        if not subject:
            subject = Subject.objects.create(name=subject_name)

        # Download and process the PDF
        pdf_path = os.path.join(settings.MEDIA_ROOT, os.path.basename(pdf_url))
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                if start_page < 1 or end_page > len(pdf.pages) or start_page > end_page:
                    raise ValueError("Invalid page range.")
                selected_text = ""
                for page_num in range(start_page - 1, end_page):
                    selected_text += pdf.pages[page_num].extract_text()
        except Exception as e:
            return render(request, 'core/test_creation.html', {
                'error': f"Error processing PDF: {str(e)}"
            })

        # Generate questions using OpenAI
        try:
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=f"Generate 10 multiple-choice questions with 4 options each (1 correct) based on the following text:\n\n{selected_text}",
                max_tokens=1500,
                temperature=0.7
            )
            questions = response.choices[0].text.strip()
        except Exception as e:
            return render(request, 'core/test_creation.html', {
                'error': f"Error generating questions: {str(e)}"
            })

        # Save the test
        test = Test.objects.create(
            title=f"{subject_name} Grade {grade} Test",
            subject=subject,
            grade=grade,
            question_data=questions
        )

        # Redirect to the test-taking page
        return redirect('take_test', test_id=test.id)

    return redirect('test_textbook')


def take_test_view(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if request.method == 'POST':
        # Process submitted answers (not implemented here)
        return redirect('test_result', test_id=test.id)

    return render(request, 'core/take_test.html', {'test': test})

@login_required
def profile_view(request):
    tests = Test.objects.all()  # Fetch all tests or filter as needed
    context = {
        'username': request.user.username,  # Pass the logged-in user's username
        'tests': tests,  # Pass the tests queryset
    }
    return render(request, 'core/profile.html', context)
def test_create_view(request):
    return render(request, 'core/test_create.html')

def test_grade_view(request):
    return render(request, 'core/test_grade.html')

def test_textbook_view(request):
    return render(request, 'core/test_textbook.html')

def test_subject_view(request):
    return render(request, 'core/test_subject.html')

def test_result_view(request):
    return render(request, 'core/test_result.html')

def test_question_view(request):
    return render(request, 'core/test_question.html')

def test_pages_daysleft_view(request):
    return render(request, 'core/test_pages_daysleft.html')
def home_view(request):
    return render(request, 'base.html')

def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
           
            Profile.objects.create(user=user) 
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/dashboard.html', {'form': form})

import logging

logger = logging.getLogger(__name__)

class CustomLoginView(LoginView):
    template_name = 'core/login.html'
    
    def form_valid(self, form):
        logger.info(f"User {form.cleaned_data['username']} is attempting to log in.")
        return super().form_valid(form)

    def get_success_url(self):
        return '/dashboard/'

MAX_FILE_SIZE = 500 * 1024 * 1024

from django.shortcuts import render
from .models import Test

def dashboard_view(request):
    tests = Test.objects.all()  # Fetch all tests
    return render(request, 'core/dashboard.html', {'tests': tests})

def test_list_view(request):
    tests = Test.objects.all()  # Fetch all tests
    selected_test_id = request.GET.get('test_id')  # Get the selected test ID from the query parameters
    selected_test = None
    questions = None

    if selected_test_id:
        selected_test = get_object_or_404(Test, id=selected_test_id)
        questions = selected_test.question_data.split("\n\n")  

    return render(request, 'core/test_list.html', {
        'tests': tests,
        'selected_test': selected_test,
        'questions': questions,
    })



def test_list_view(request):
    subjects = Subject.objects.prefetch_related('tests').all()
    return render(request, 'core/test_list.html', {'subjects': subjects})

def ranking_view(request):
    if request.method == 'GET':
        context = {
            'username': request.user.username,  # Pass the logged-in user's username
            'rankings': [
                {'username': 'JohnDoe', 'score': 95},
                {'username': 'JaneSmith', 'score': 90},
                {'username': 'AliceBrown', 'score': 85},
            ]
        }
        return render(request, 'core/ranking.html', context)

from transformers import pipeline as transformers_pipeline

def generate_test_view(request):
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        try:
            # Process PDF
            pdf_file = request.FILES['pdf_file']
            with pdfplumber.open(pdf_file) as pdf:
                text = "".join(page.extract_text() for page in pdf.pages[:5])  # Limit to first 5 pages

            # Language detection
            language = detect(text)

            # Translation (if needed)
            if language != "bg":
                try:
                    translator = transformers_pipeline(
                        "translation_en_to_bg", 
                        model="Helsinki-NLP/opus-mt-en-bg",
                        device="cpu"
                    )
                    text = translator(text[:1000])[0]['translation_text']  # Limit input size
                except Exception as e:
                    return render(request, 'core/test_result.html', {
                        'error': f"Translation failed: {str(e)}"
                    })

            # Use smaller model for test generation
            try:
                generator = transformers_pipeline(
                    "text-generation",
                    model="distilgpt2",  # Smaller model
                    device="cpu",
                    max_length=500
                )
                
                prompt = f"Create a test in Bulgarian based on: {text[:500]}"  # Limit prompt size
                generated_test = generator(prompt)[0]['generated_text']

                return render(request, 'core/test_result.html', {
                    'test': generated_test
                })
                
            except Exception as e:
                return render(request, 'core/test_result.html', {
                    'error': f"Test generation failed: {str(e)}"
                })

        except Exception as e:
            return render(request, 'core/test_result.html', {
                'error': f"Processing failed: {str(e)}"
            })

    return render(request, 'core/test_result.html', {
        'error': 'Invalid request method'
    })
