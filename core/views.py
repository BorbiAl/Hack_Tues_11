from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.http import HttpResponse
from .models import Test
from .forms import CustomUserCreationForm
import os
import logging
import openai
import PyPDF2
import json
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
import pytesseract
from pdf2image import convert_from_path
from PIL import Image 
from PyPDF2 import PdfReader

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

def test_question_view(request, textbook_id):
    """View to display and handle test questions loaded from Rag questions."""
    # Retrieve the textbook and its associated Rag instance
    textbook = get_object_or_404(TestTextbook, id=textbook_id)
    rag = get_object_or_404(Rag, textbook=textbook)
    
    # Load the questions from the Rag instance. Assume the TestQuestion model
    # contains 'question_text', 'answer', and 'options' attributes.
    questions_qs = rag.get_questions()
    questions = []
    for q in questions_qs:
        questions.append({
            'question': q.question_text,
            'answer': q.answer,         # Ensure your model has this field
            'options': q.options,       # Ensure your model has this field (list or similar structure)
        })

    # If the session hasn't been initialized with questions, do so once.
    if 'questions' not in request.session:
        request.session['questions'] = questions
        request.session['current_question_index'] = 0
        request.session['results'] = []
    
    current_question_index = request.session.get('current_question_index', 0)
    session_questions = request.session.get('questions', questions)

    if request.method == 'POST':
        # Process the submitted answer.
        selected_answer = request.POST.get('selected_answer', '')
        current_question = session_questions[current_question_index]
        correct_answer = current_question.get('answer', '')
        is_correct = (selected_answer == correct_answer)

        # Record the result with minimal session data
        results = request.session.get('results', [])
        results.append({
            'selected_answer': selected_answer,
            'is_correct': is_correct
        })
        request.session['results'] = results

        # Increment the current question index.
        current_question_index += 1
        request.session['current_question_index'] = current_question_index

        # Redirect to the next question or the test result view.
        if current_question_index < len(session_questions):
            return redirect('test_question', textbook_id=textbook_id)
        else:
            return redirect('test_result', textbook_id=textbook_id)

    else:
        # GET request: display the current question.
        if current_question_index < len(session_questions):
            current_question = session_questions[current_question_index]
            context = {
                'question': current_question.get('question', ''),
                'answers': current_question.get('options', []),
                'current_question_index': current_question_index + 1,
                'total_questions': len(session_questions),
            }
            return render(request, 'core/test_question.html', context)
        else:
            return redirect('test_result', textbook_id=textbook_id)

def test_creation_view(request):
    """View to generate test questions from a selected PDF."""
    if request.method == 'POST':
        try:
            # Extract form data
            pdf_url = request.POST.get('pdf_url')
            start_page = int(request.POST.get('start_page', 0))
            end_page = int(request.POST.get('end_page', 0))

            # Validate form input
            if not pdf_url or start_page <= 0 or end_page <= 0 or start_page > end_page:
                raise ValueError("Invalid form data")

            # Load PDF content
            pdf_path = os.path.join(settings.MEDIA_ROOT, os.path.basename(pdf_url))
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                if start_page > len(pdf_reader.pages) or end_page > len(pdf_reader.pages):
                    raise ValueError("Page range exceeds the number of pages in the PDF.")

                # Extract text from the specified pages
                extracted_texts = [
                    pdf_reader.pages[page_num].extract_text()
                    for page_num in range(start_page - 1, end_page)
                ]

            # Use RAG model to generate questions
            questions = rag_model.generate_questions_from_pages(extracted_texts)
            if not questions:
                raise ValueError("No questions were generated by the RAG model.")

            # Store questions in session
            request.session['questions'] = questions
            request.session['current_question_index'] = 0

            # Redirect to the loading page
            return redirect('test_loading')

        except Exception as e:
            logger.error(f"Error in test_creation_view: {e}")
            return redirect('test_textbook')

    return redirect('test_textbook')

from datetime import date

def test_result_view(request):
    """View to display test results."""
    if request.user.is_authenticated:
        profile = request.user.profile
        today = date.today()
    
        if profile.last_test_date == today:
            profile.streak += 1  # Increment streak
        else:
            # Check if the streak is not continuous (last test date is not today)
            if profile.last_test_date != today:
                if (today - profile.last_test_date).days == 1:
                    pass
                else:
                    # Reset streak to 0 if it's not the next day
                    profile.streak = 0
            else:
                profile.streak = 1  # Reset streak to 1 for a new day

        # Update the last test date
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
    


pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

@csrf_exempt
def generate_questions(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pdf_url = data.get('pdf_url')
            start_page = data.get('start_page')
            end_page = data.get('end_page')

            if not (pdf_url and start_page and end_page):
                return JsonResponse({"error": "Липсват задължителни полета."}, status=400)

            # Load PDF content from the provided URL
            pdf_path = os.path.join(settings.MEDIA_ROOT, os.path.basename(pdf_url))
            if not os.path.exists(pdf_path):
                return JsonResponse({"error": "PDF файлът не е намерен."}, status=404)

            # Extract text from PDF pages
            extracted_texts = []
            pdf_reader = PdfReader(pdf_path)
            for page_num in range(start_page - 1, end_page):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text.strip():  # If text is extracted successfully
                    extracted_texts.append(text)
                else:
                    # If no text is extracted, use OCR on the page image
                    images = convert_from_path(pdf_path, first_page=page_num + 1, last_page=page_num + 1, dpi=300)
                    for image in images:
                        ocr_text = pytesseract.image_to_string(image, lang='bul')  # Use Bulgarian language for OCR
                        extracted_texts.append(ocr_text)

            # Combine extracted text into a single prompt
            combined_text = "\n".join(extracted_texts).strip()

            if not combined_text:
                return JsonResponse({"error": "No text could be extracted from the selected pages. Please try different pages."}, status=400)

            prompt = (
                "Ти си AI, който генерира въпроси с множество отговори от текст. "
                "Като използваш следното съдържание, генерирай списък от въпроси с четири опции за отговор, "
                "и посочи правилния отговор за всеки въпрос:\n\n"
                f"{combined_text}\n\n"
                "Форматирай отговора си като JSON масив от обекти, където всеки обект съдържа "
                "'question' (въпрос), 'options' (списък от четири стринга) и 'answer' (правилният отговор)."
            )

            # Use OpenAI API to generate questions
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Ти си полезен асистент."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )

            questions = json.loads(response['choices'][0]['message']['content'])

            if not questions:
                return JsonResponse({"error": "OpenAI не успя да генерира въпроси."}, status=400)
            return JsonResponse({"questions": questions})
        except Exception as e:
            return JsonResponse({"error": "Възникна грешка.", "details": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Невалиден метод на заявка."}, status=400)