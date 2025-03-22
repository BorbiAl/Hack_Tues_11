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
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/signup.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = 'core/login.html'

MAX_FILE_SIZE = 500 * 1024 * 1024

def dashboard_view(request):
    tests = Test.objects.all()  # Fetch all tests
    return render(request, 'core/dashboard.html', {
        'tests': tests,
        'username': request.user.username,  # Pass the logged-in user's username
    })

def test_list_view(request):
    tests = Test.objects.all()
    return render(request, 'core/test_list.html', {'tests': tests})

def test_creation_view(request):
    if request.method == 'POST':
        pdf_file = request.FILES.get('pdf_file')
        start_page = int(request.POST.get('start_page', 1))
        end_page = int(request.POST.get('end_page', 1))
        due_date = request.POST.get('due_date')
        selected_subject = request.POST.get('subject')  # Get the selected subject
        selected_grade = request.POST.get('grade')  # Get the selected grade

        if pdf_file.size > 500 * 1024 * 1024:  # 500 MB limit
            return render(request, 'core/test_creation.html', {
                'error': "The uploaded file exceeds the maximum allowed size of 500 MB."
            })

        try:
            with pdfplumber.open(pdf_file) as pdf:
                if start_page < 1 or end_page > len(pdf.pages) or start_page > end_page:
                    raise ValidationError("Invalid page range selected.")
                selected_text = ""
                for page_num in range(start_page - 1, end_page):
                    selected_text += pdf.pages[page_num].extract_text()
        except Exception as e:
            return render(request, 'core/test_creation.html', {
                'error': f"An error occurred while processing the PDF: {str(e)}"
            })

        try:
            parsed_due_date = parse_date(due_date)
            if not parsed_due_date:
                raise ValidationError("Invalid due date format.")
        except ValidationError as e:
            return render(request, 'core/test_creation.html', {
                'error': f"Invalid due date: {str(e)}"
            })

        # Check if a test already exists for the selected subject and grade
        subject = Subject.objects.filter(name=selected_subject).first()
        if not subject:
            subject = Subject.objects.create(name=selected_subject, description="Default description")

        existing_test = Test.objects.filter(subject=subject, title=f"Grade {selected_grade} Test").first()
        if existing_test:
            # Redirect to the existing test
            return redirect('take_test', test_id=existing_test.id)

        # Generate AI-based questions using OpenAI
        try:
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=f"Generate 5 multiple-choice questions based on the following text:\n\n{selected_text}",
                max_tokens=500,
                temperature=0.7
            )
            questions = response.choices[0].text.strip()
        except Exception as e:
            return render(request, 'core/test_creation.html', {
                'error': f"An error occurred while generating questions: {str(e)}"
            })

        test = Test.objects.create(
            title=f"Grade {selected_grade} Test",
            question_data=questions,  
            due_date=parsed_due_date,
            subject=subject
        )

        return redirect('take_test', test_id=test.id)

    # Pass subjects and grades to the template for selection
    subjects = Subject.objects.all()
    grades = range(1, 13)  # Assuming grades 1 to 12
    return render(request, 'core/test_creation.html', {'subjects': subjects, 'grades': grades})

def test_textbook_view(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    pdf_filename = test.get_pdf_filename()
    pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_filename) if pdf_filename else None

    context = {
        'test': test,
        'pdf_filename': pdf_filename,
        'pdf_exists': os.path.exists(pdf_path) if pdf_path else False,
    }
    return render(request, 'core/test_textbook.html', context)
def take_test_view(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    questions = test.question_data.split("\n\n")  # Split questions into a list
    total_questions = len(questions)
    current_question = int(request.GET.get('question', 1))

    if current_question > total_questions or current_question < 1:
        return redirect('test_result', test_id=test_id)  # Redirect to results if out of range

    question = questions[current_question - 1] if total_questions > 0 else None

    progress = (current_question / total_questions) * 100 if total_questions > 0 else 0

    return render(request, 'core/take_test.html', {
        'test': test,
        'question': question,
        'current_question': current_question,
        'total_questions': total_questions,
        'progress': progress,
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

def generate_test_view(request):
    if request.method == 'POST' and request.FILES.get('pdf_file'):

        pdf_file = request.FILES['pdf_file']
        with pdfplumber.open(pdf_file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()


        language = detect(text)


        if language != "bg":
            translator = pipeline("translation", model="Helsinki-NLP/opus-mt-mul-bg")
            translated = translator(text, max_length=512)
            text = translated[0]['translation_text']


        model_name = "gpt2"  
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)

        prompt = f"""
        Based on the following content, create a single test in Bulgarian with all question types:
        1. A multiple-choice question with one correct answer and two incorrect answers.
        2. A matching question where terms are matched with their meanings.
        3. A typing question where the user must type the correct answer.

        Content:
        {text}

        Provide the test in Bulgarian.
        """
        inputs = tokenizer.encode(prompt, return_tensors="pt")
        outputs = model.generate(inputs, max_length=1000000, num_return_sequences=1, temperature=0.7)
        generated_test = tokenizer.decode(outputs[0], skip_special_tokens=True)

        return render(request, 'core/test_result.html', {'test': generated_test})

    return json({'error': 'Invalid request method'}, status=405)
