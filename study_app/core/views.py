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
    return render(request, 'core/dashboard.html')
    
def profile_view(request):
    context = {
        'username': 'JohnDoe',
        'joined_date': '2025-01-01',
    }
    return render(request, 'core/profile.html', context)

def test_list_view(request):
    tests = Test.objects.all()
    return render(request, 'core/test_list.html', {'tests': tests})

def test_creation_view(request):
    if request.method == 'POST':

        pdf_file = request.FILES.get('pdf_file')
        start_page = int(request.POST.get('start_page', 1))
        end_page = int(request.POST.get('end_page', 1))
        due_date = request.POST.get('due_date')


        if pdf_file.size > MAX_FILE_SIZE:
            return render(request, 'core/test_creation.html', {
                'error': f"The uploaded file exceeds the maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024)} MB."
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


        return render(request, 'core/test_creation.html', {
            'selected_text': selected_text,
            'start_page': start_page,
            'end_page': end_page,
            'due_date': due_date,
        })


    return render(request, 'core/test_creation.html')

def take_test_view(request, test_id):
    test = Test.objects.get(id=test_id)
    questions = json.loads(test.questions) 
    total_questions = len(questions)
    current_question = int(request.GET.get('question', 1)) 


    progress = (current_question / total_questions) * 100


    question = questions[current_question - 1]

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
            'rankings': [
                {'username': 'JohnDoe', 'score': 95},
                {'username': 'JaneSmith', 'score': 90},
                {'username': 'AliceBrown', 'score': 85},
            ]
        }
        return render(request, 'core/ranking.html', context)
    return json({'error': 'Invalid request method'}, status=405)

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
