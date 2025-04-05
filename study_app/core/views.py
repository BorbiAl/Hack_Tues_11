import openai
import pdfplumber
from langdetect import detect
from transformers import pipeline as transformers_pipeline
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

import logging
logger = logging.getLogger(__name__)

def test_textbook_view(request):
    # Path to the media directory
    media_path = settings.MEDIA_ROOT
    files = []

    # Log media path for debugging
    logger.info(f"Media path: {media_path}")
    logger.info(f"Directory exists: {os.path.exists(media_path)}")
    logger.info(f"Directory contents: {os.listdir(media_path)}")

    # Fetch all PDF files in the media directory and subdirectories
    for root, dirs, filenames in os.walk(media_path):
        logger.info(f"Scanning directory: {root}")
        logger.info(f"Files found: {1}")
        for file_name in filenames:
            if file_name.lower().endswith('.pdf'):
                relative_path = os.path.relpath(os.path.join(root, file_name), media_path)
                file_data = {
                    'name': os.path.splitext(file_name)[0],  # Remove .pdf extension
                    'url': f"{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"
                }
                files.append(file_data)
                logger.info(f"Found PDF file: {file_data}")
            else:
                logger.info(f"Skipping non-PDF file: {file_name}")

    context = {
        'files': sorted(files, key=lambda x: x['name'])  # Sort alphabetically
    }

    logger.info(f"Files being passed to template: {context['files']}")

    return render(request, 'core/test_textbook.html', context)
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
                prompt=f"Generate 10 multiple-choice questions with 4 options each (mark correct answer with *) based on the following text. Format as JSON array with fields: question, answers (array of 4 strings), correct_answer (index 0-3):\n\n{selected_text}",
                max_tokens=1500,
                temperature=0.7
            )
            questions = json.loads(response.choices[0].text.strip())
        except Exception as e:
            return render(request, 'core/test_creation.html', {
                'error': f"Error generating questions: {str(e)}"
            })

        # Save the test
        test = Test.objects.create(
            title=f"{subject_name} Grade {grade} Test",
            subject=subject,
            grade=grade,
            question_data=json.dumps(questions) #Store as JSON string
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
    if request.method == 'POST':
        # Get first question from predefined questions
        questions = get_random_questions(10) # Placeholder function
        first_question = questions[0]

        # Store questions in session
        request.session['questions'] = questions
        request.session['current_question_index'] = 0

        return render(request, 'core/test_question.html', {
            'question': first_question['question'],
            'answers': first_question['options'],
            'current_question_index': 1,
            'correct_answer': first_question['answer']
        })

    # If GET request, redirect to test list
    return redirect('test_textbook')


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
    return render(request, 'core/signup.html', {'form': form})

import logging

logger = logging.getLogger(__name__)

from django.contrib.auth import authenticate
from django.contrib import messages

class CustomLoginView(LoginView):
    template_name = 'core/login.html'

    def form_valid(self, form):
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            logger.info(f"User {username} successfully logged in.")
            login(self.request, user)
            return super().form_valid(form)
        else:
            logger.warning(f"Failed login attempt for username: {username}")
            messages.error(self.request, 'Invalid username or password')
            return self.form_invalid(form)

    def get_success_url(self):
        return '/dashboard/'

MAX_FILE_SIZE = 500 * 1024 * 1024

from django.shortcuts import render
from .models import Test

def dashboard_view(request):
    tests = Test.objects.all()  # Fetch all tests
    context = {
        'tests': tests,
        'username': request.user.username
    }
    return render(request, 'core/dashboard.html', context)

def test_list_view(request):
    tests = Test.objects.all()  # Fetch all tests
    selected_test_id = request.GET.get('test_id')  # Get the selected test ID from the query parameters
    selected_test = None
    questions = None

    if selected_test_id:
        selected_test = get_object_or_404(Test, id=selected_test_id)
        questions = json.loads(selected_test.question_data) #Load JSON string

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

# Global variable for cached model
_model_cache = None

def get_cached_model():
    global _model_cache
    if _model_cache is None:
        _model_cache = transformers_pipeline(
            "text-generation",
            model="distilgpt2",
            device="cpu"
        )
    return _model_cache

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

            # Use cached model for test generation
            try:
                generator = get_cached_model()

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

def get_random_questions(num_questions):
    # Placeholder function:  Replace with actual question retrieval logic
    # This should fetch questions from a database or other source.
    # For now, it returns a dummy list of questions.
    LITERATURE_QUESTIONS = [
    {
        'question': 'Кой е главният герой в разказа „Косачи" на Елин Пелин?',
        'options': ['Станчо', 'Благолажът', 'Иван', 'Дядо Йото'],
        'answer': 1
    },
    {
        'question': 'Какво разказва Благолажът на косачите?',
        'options': ['Истории за героични битки', 'Легенди за съкровища', 'Забавни истории и любовни разкази', 'Приказки за животни'],
        'answer': 2
    },
    {
        'question': 'Каква роля играе природата в разказа „Косачи"?',
        'options': ['Създава тайнствена атмосфера', 'Представя страховете на героите', 'Описва селското общество', 'Подчертава чувствата на героите'],
        'answer': 3
    },
    {
        'question': 'Кое изкуство е най-силно застъпено в „Косачи"?',
        'options': ['Живопис', 'Танц', 'Изкуството на словото', 'Музиката'],
        'answer': 2
    },
    {
        'question': 'Какъв е Благолажът като човек?',
        'options': ['Силен и мълчалив', 'Весел и разговорлив', 'Срамежлив и затворен', 'Учен и строг'],
        'answer': 1
    },
    {
        'question': 'Какъв е ефектът от песента, която героите пеят в края на „Косачи"?',
        'options': ['Подчертава тъгата им', 'Разкрива вътрешния им гняв', 'Изразява единството им', 'Показва недоволство от живота'],
        'answer': 2
    },
    {
        'question': 'Кой е авторът на стихотворението „Художник"?',
        'options': ['Христо Смирненски', 'Иван Вазов', 'Веселин Ханчев', 'Гео Милев'],
        'answer': 2
    },
    {
        'question': 'Какво рисува детето в стихотворението „Художник"?',
        'options': ['Картина с природата', 'Мечтания свят', 'Домашни животни', 'Битки и войни'],
        'answer': 1
    },
    {
        'question': 'Какви са чувствата на детето към рисуването в стихотворението „Художник"?',
        'options': ['Страх и несигурност', 'Безразличие', 'Радост и вдъхновение', 'Тъга и скука'],
        'answer': 2
    },
    {
        'question': 'С какви средства е изразено изкуството в стихотворението „Художник"?',
        'options': ['С гатанки', 'С песни', 'С багри и четка', 'С народни приказки'],
        'answer': 2
    },
    {
        'question': 'Какво символизира четката в стихотворението?',
        'options': ['Оръжие', 'Природа', 'Творческа свобода', 'Труд'],
        'answer': 2
    },
    {
        'question': 'Какво е основното послание на стихотворението „Художник"?',
        'options': ['Изкуството ни носи радост и свобода', 'Трудът е по-важен от мечтите', 'Детството е време за игри', 'Всеки трябва да стане художник'],
        'answer': 0
    },
    {
        'question': 'В кой роман се намира откъсът „Представлението"?',
        'options': ['„Гераците"', '„Под игото"', '„Бай Ганьо"', '„Немили-недраги"'],
        'answer': 1
    },
    {
        'question': 'Какво представление гледат героите в откъса?',
        'options': ['Народен танц', 'Оперета', 'Театрална постановка', 'Цирково шоу'],
        'answer': 2
    },
    {
        'question': 'Как се чувстват зрителите по време на представлението?',
        'options': ['Безразлични', 'Натъжени', 'Вдъхновени и развълнувани', 'Отегчени'],
        'answer': 2
    },
    {
        'question': 'Каква е целта на представлението според Вазов?',
        'options': ['Да покаже чуждестранна култура', 'Да създаде комична ситуация', 'Да обедини народа чрез изкуството', 'Да насърчи децата да учат'],
        'answer': 2
    },
    {
        'question': 'Как героите приемат участието си в театъра?',
        'options': ['С досада', 'С гордост и ентусиазъм', 'С неразбиране', 'С неувереност'],
        'answer': 1
    },
    {
        'question': 'Кой герой организира представлението в Бяла черква?',
        'options': ['Чорбаджи Марко', 'Бай Марко', 'Кириак Стефчов', 'Кандов'],
        'answer': 3
    },
    {
        'question': 'Какво показва сцената с представлението за българите под османско владичество?',
        'options': ['Загуба на идентичност', 'Липса на културен живот', 'Желание за изразяване чрез изкуството', 'Страх от промяна'],
        'answer': 2
    },
    {
        'question': 'Каква е връзката между трите произведения в раздела „Човекът и изкуството"?',
        'options': ['Във всички се говори за любовта', 'Във всички присъства тема за свобода', 'Изкуството е представено като важна част от човешкия живот', 'Всички са написани през 19 век'],
        'answer': 2
    }
]
    return LITERATURE_QUESTIONS[:num_questions]



