from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.http import HttpResponse
from .models import Test, Subject  # Ensure Subject is imported
from .forms import CustomUserCreationForm
import os
import logging
import openai
from openai import OpenAI
import json
from datetime import date
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from PyPDF2 import PdfReader  
import fitz
from PIL import Image, ImageEnhance  
import pytesseract  
from .models import Subject 
from pdf2image import convert_from_path
from django.core.cache import cache
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO


# Initialize logger
logger = logging.getLogger(__name__) 

# OpenAI API Key
openai.api_key = settings.OPENAI_API_KEY


def test_textbook_view(request):
    """View to display available textbooks."""
    media_path = settings.MEDIA_ROOT
    files = []

    # Fetch all PDF files in the media directory
    for root, _, filenames in os.walk(media_path):
        for file_name in filenames:
            if file_name.lower().endswith('.pdf'):
                relative_path = os.path.relpath(os.path.join(root, file_name), media_path)
                files.append({
                    'name': os.path.splitext(file_name)[0],
                    'url': f"{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"
                })

    context = {'files': sorted(files, key=lambda x: x['name'])}
    return render(request, 'core/test_textbook.html', context)


def parse_generated_questions(generated_text):
    """Parse AI-generated text into structured questions."""
    questions = []
    for block in generated_text.split("\n\n"):
        lines = block.split("\n")
        if len(lines) < 5:
            continue
        question = lines[0]
        options = lines[1:5]
        correct_answer = lines[5].split(":")[1].strip() if len(lines) > 5 else None
        questions.append({
            'question': question,
            'options': options,
            'answer': correct_answer
        })
    return questions


@csrf_exempt
def test_question_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            questions = data.get('questions', [])
            # Save or process the questions as needed
            request.session['questions'] = questions
            return JsonResponse({"message": "Questions received successfully."})
        except Exception as e:
            return JsonResponse({"error": "Failed to process questions.", "details": str(e)}, status=500)
    elif request.method == 'GET':
        # Render the test_question page for GET requests
        questions = request.session.get('questions', [])
        return render(request, 'core/test_question.html', {'questions': questions})
    else:
        return JsonResponse({"error": "Invalid request method."}, status=405)

def test_result_view(request):
    """View to display test results."""
    if request.user.is_authenticated:
        profile = request.user.profile
        today = date.today()

        if profile.last_test_date == today:
            profile.streak += 1
        elif profile.last_test_date and (today - profile.last_test_date).days == 1:
            profile.streak += 1
        else:
            profile.streak = 1
        profile.last_test_date = today
        profile.save()

    results = request.session.get('results', [])
    total_questions = len(results)
    correct_answers = sum(1 for result in results if result['is_correct'])
    wrong_answers_count = total_questions - correct_answers

    context = {
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'wrong_answers_count': wrong_answers_count,
        'results': results,
        'streak': request.user.profile.streak if request.user.is_authenticated else 0,
    }
    return render(request, 'core/test_result.html', context)


@login_required
def profile_view(request):
    """View to display user profile and tests."""
    tests = Test.objects.all()
    context = {
        'username': request.user.username,
        'tests': tests,
        'streak': request.user.profile.streak if request.user.is_authenticated else 0,
    }
    return render(request, 'core/profile.html', context)


class CustomLoginView(LoginView):
    """Custom login view."""
    template_name = 'core/login.html'

    def form_valid(self, form):
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            login(self.request, user)
            return super().form_valid(form)
        else:
            return HttpResponse("<h1>Invalid username or password</h1>")

    def get_success_url(self):
        return '/dashboard/'


def signup_view(request):
    """View to handle user signup."""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/signup.html', {'form': form})


def home_view(request):
    """Home view."""
    return render(request, 'base.html')


def dashboard_view(request):
    """Dashboard view."""
    if request.user.is_authenticated:
        is_first_login = request.user.last_login is None
        context = {
            'username': request.user.username,
            'tests': Test.objects.all(),
            'streak': request.user.profile.streak if request.user.is_authenticated else 0,
            'is_first_login': is_first_login,
        }
        return render(request, 'core/dashboard.html', context)
    else:
        return redirect('login')


def ranking_view(request):
    """View to display rankings."""
    if request.method == 'GET':
        context = {
            'username': request.user.username,
            'rankings': [
                {'username': 'JohnDoe', 'score': 95},
                {'username': 'JaneSmith', 'score': 90},
                {'username': 'AliceBrown', 'score': 85},
            ],
            'streak': request.user.profile.streak if request.user.is_authenticated else 0,
        }
        return render(request, 'core/ranking.html', context)

def summarize_text(text):
    """Summarize text using OpenAI API."""
    if not text:
        return {'error': 'Text is required'}

    prompt = f"Summarize the following text to maximum 3000 tokens:\n{text}"

    try:
        # Remove this line as OpenAI is already initialized with `openai.api_key`
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=3000
        )
        summary = response.choices[0].message.content.strip()
        return {'summary': summary}
    except Exception as e:
        return {'error': f'OpenAI API error: {str(e)}'}

def preprocess_and_ocr(image_bytes):
    image = Image.open(BytesIO(image_bytes)).convert('L')  # Correct usage of BytesIO
    image = ImageEnhance.Contrast(image).enhance(1.5)
    image = ImageEnhance.Sharpness(image).enhance(1.5)
    return pytesseract.image_to_string(image, lang='bul', config='--psm 6')

def extract_images_with_fitz(pdf_path, start_page, end_page):
    doc = fitz.open(pdf_path)
    images = []
    for i in range(start_page - 1, end_page):
        pix = doc.load_page(i).get_pixmap(dpi=100)
        images.append(pix.tobytes("png"))
    return images

@csrf_exempt
def generate_questions(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)

    try:
        data = json.loads(request.body)
        pdf_filename = data.get('pdf_filename')
        start_page = int(data['start_page'])
        end_page = int(data['end_page'])
    except (KeyError, ValueError):
        return JsonResponse({'error': 'Invalid input data'}, status=400)

    pdf_path = os.path.join(settings.MEDIA_ROOT, os.path.basename(pdf_filename))
    if not os.path.exists(pdf_path):
        return JsonResponse({'error': 'PDF file not found'}, status=404)

    try:
        # Step 1: Extract images from pages with Fitz (fast)
        images_bytes = extract_images_with_fitz(pdf_path, start_page, end_page)

        # Step 2: Run OCR on images in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            texts = list(executor.map(preprocess_and_ocr, images_bytes))

        # Step 3: Summarize and generate questions
        questions = []
        for i, text in enumerate(texts):
            summarized = summarize_text(text[:2000]).get('summary', '')
            prompt = (
                "Прочети следния текст и създай въпроси с 4 възможни отговора (само един правилен), като питаш за самата информация ако предположиш, че читателят не е чел текста. \n"
                "Форматът да бъде:\n"
                "Въпрос: <тук въпросът>\nА) <отговор 1>\nБ) <отговор 2>\nВ) <отговор 3>\nГ) <отговор 4>\nПравилен отговор: <буква>\n\n"
                f"{summarized}"
            )
            client = OpenAI(api_key=settings.OPENAI_API_KEY)  # Ensure OpenAI client is initialized correctly
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=600,
            )
            if response.choices and response.choices[0].message:
                questions.extend(parse_generated_questions(response.choices[0].message.content.strip()))
            if len(questions) >= 10:
                break

        return JsonResponse({'questions': questions[:10]})

    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)



@login_required 
def save_test(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            date = data.get('date')
            subject_name = data.get('subject')

            if not date or not subject_name:
                return JsonResponse({'error': 'Date and subject are required'}, status=400)

            # Get or create the subject
            subject, _ = Subject.objects.get_or_create(name=subject_name)

            # Save the test for the current user
            test, created = Test.objects.get_or_create(
                user=request.user,
                date=date,
                defaults={'subject': subject}
            )

            if not created:
                test.subject = subject
                test.save()

            return JsonResponse({'message': 'Test saved successfully', 'date': date, 'subject': subject.name})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def get_saved_tests(request):
    """Fetch saved tests for the current user."""
    month = request.GET.get('month')
    year = request.GET.get('year')

    try:
        month = int(month)
        year = int(year)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Month and year must be integers'}, status=400)

    tests = Test.objects.filter(
        user=request.user,
        date__year=year,
        date__month=month
    ).values('date', 'subject__name')

    return JsonResponse({'tests': list(tests)})