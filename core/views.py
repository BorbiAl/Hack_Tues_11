from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.http import HttpResponse
from django.core.cache import cache
from django.core.paginator import Paginator
from .models import Test, Subject
from .forms import CustomUserCreationForm
import os
import logging
import openai
import json
from datetime import date
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from PyPDF2 import PdfReader
import fitz
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from openai import OpenAI
from .utils import parse_generated_questions
from concurrent.futures import ThreadPoolExecutor
from nltk.tokenize import sent_tokenize
from django.core.cache import cache
import nltk

nltk.download('punkt_tab')

# Initialize logger
logger = logging.getLogger(__name__)

# OpenAI API Key
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENAI_API_KEY,
)


def test_textbook_view(request):
    """View to display available textbooks with caching."""
    media_path = settings.MEDIA_ROOT
    files = cache.get('textbook_files')

    if not files:
        files = []
        for root, _, filenames in os.walk(media_path):
            for file_name in filenames:
                if file_name.lower().endswith('.pdf'):
                    relative_path = os.path.relpath(os.path.join(root, file_name), media_path)
                    files.append({
                        'name': os.path.splitext(file_name)[0],
                        'url': f"{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"
                    })
        cache.set('textbook_files', files, timeout=60 * 60)  # Cache for 1 hour

    context = {'files': sorted(files, key=lambda x: x['name'])}
    return render(request, 'core/test_textbook.html', context)


@csrf_exempt
def test_question_view(request):
    """View to display the generated question."""
    question = request.session.get('generatedQuestion', None)

    if not question:
        return render(request, 'core/test_question.html', {'error': 'No question found. Please generate a test first.'})

    return render(request, 'core/test_question.html', {'question': question})


def test_result_view(request):
    """View to display test results with optimized streak calculation."""
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

    # Getting results from the session
    results = request.session.get('results', None)
    if not results:
        return render(request, 'core/test_result.html', {'error': 'No results found. Please complete the test first.'})

    # Calculate stats
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
    """View to display user profile and tests with optimized queries."""
    tests = Test.objects.select_related('subject').all()
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


@csrf_exempt
def generate_questions(request):
    """Generate questions with optimized text extraction and parallel processing."""
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
        images = convert_from_path(pdf_path, first_page=start_page, last_page=end_page)
    except Exception as e:
        return JsonResponse({'error': f'PDF to image conversion failed: {str(e)}'}, status=500)

    def process_page(img):
        return pytesseract.image_to_string(img, lang='bul')

    with ThreadPoolExecutor() as executor:
        results = executor.map(process_page, images)

    extracted_text = '\n'.join(results)

    def truncate_text(text, max_sentences=10):
        sentences = sent_tokenize(text)
        return ' '.join(sentences[:max_sentences])

    prompt = (
        "Прочети следния текст и създай поне 6 въпроса с 4 възможни отговора (само един правилен), като не използваш изрази от типа на 'от текста'.\n"
        "Форматът да бъде:\n"
        "Въпрос: <тук въпросът>\n"
        "А) <отговор 1>\n"
        "Б) <отговор 2>\n"
        "В) <отговор 3>\n"
        "Г) <отговор 4>\n"
        "Правилен отговор: <буква>\n\n"
        f"Текст:\n{truncate_text(extracted_text)}"
    )

    try:
        response = client.chat.completions.create(
            model="mistralai/mistral-small-3.1-24b-instruct:free",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        result = response.choices[0].message.content.strip()
    except Exception as e:
        return JsonResponse({'error': f'OpenAI API error: {str(e)}'}, status=500)

    return JsonResponse({'question': result})


@login_required
def save_test(request):
    """Save user tests."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            date = data.get('date')
            subject_name = data.get('subject')

            if not date or not subject_name:
                return JsonResponse({'error': 'Date and subject are required'}, status=400)

            subject, _ = Subject.objects.get_or_create(name=subject_name)

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
    """Fetch paginated saved tests for the current user."""
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

    paginator = Paginator(tests, 10)  # Show 10 tests per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return JsonResponse({'tests': list(page_obj), 'has_next': page_obj.has_next()})