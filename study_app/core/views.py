import os 
import pdfplumber
from langdetect import detect
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
from django.shortcuts import render
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date
from core.models import Test 
from core.models import Subject
import torch
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import HttpResponse
from django.shortcuts import render
from django.http import JsonResponse

# Removed unused import

def run_sql_view(request):
    # Example logic for running SQL queries (replace with your actual logic)
    if request.method == 'POST':
        sql_query = request.POST.get('sql_query', '')
        # You can add logic here to execute the SQL query securely
        # For now, we'll just return the query as a response
        return HttpResponse(f"SQL Query: {sql_query}")

    return render(request, 'core/run_sql.html')

def ranking_view(request):
    tests = Test.objects.all().order_by('-score')  # Assuming 'score' is a field in the Test model
    return render(request, 'core/ranking.html', {'tests': tests})

def login_view(request):
    return render(request, 'core/login.html')

def signup_view(request):
    return render(request, 'core/signup.html')

def dashboard_view(request):
    return render(request, 'core/dashboard.html')

def profile_view(request):
    # Example context data for the profile page
    context = {
        'username': 'JohnDoe',
        'email': 'johndoe@example.com',
        'joined_date': '2025-01-01',
    }
    return render(request, 'core/profile.html', context)

# Maximum allowed file size in bytes (e.g., 500 MB)
MAX_FILE_SIZE = 500 * 1024 * 1024
def test_list_view(request):
    tests = Test.objects.all()
    return render(request, 'core/test_list.html', {'tests': tests})

def test_creation_view(request):
    if request.method == 'POST':
        # Handle form submission
        pdf_file = request.FILES.get('pdf_file')
        start_page = int(request.POST.get('start_page', 1))
        end_page = int(request.POST.get('end_page', 1))
        due_date = request.POST.get('due_date')

        # Validate file size
        if pdf_file.size > MAX_FILE_SIZE:
            return render(request, 'core/test_creation.html', {
                'error': f"The uploaded file exceeds the maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024)} MB."
            })

        # Extract text from the selected page range
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

        # Parse and validate the due date
        try:
            parsed_due_date = parse_date(due_date)
            if not parsed_due_date:
                raise ValidationError("Invalid due date format.")
        except ValidationError as e:
            return render(request, 'core/test_creation.html', {
                'error': f"Invalid due date: {str(e)}"
            })

        # Render the preview of the selected material
        return render(request, 'core/test_creation.html', {
            'selected_text': selected_text,
            'start_page': start_page,
            'end_page': end_page,
            'due_date': due_date,
        })

    # Render the form for GET requests
    return render(request, 'core/test_creation.html')

def take_test_view(request, test_id):
    test = Test.objects.get(id=test_id)
    questions = json.loads(test.questions)  # Assume questions are stored as JSON
    total_questions = len(questions)
    current_question = int(request.GET.get('question', 1))  # Default to the first question

    # Calculate progress
    progress = (current_question / total_questions) * 100

    # Get the current question
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
    # Example context data for the ranking page
    context = {
        'rankings': [
            {'username': 'JohnDoe', 'score': 95},
            {'username': 'JaneSmith', 'score': 90},
            {'username': 'AliceBrown', 'score': 85},
        ]
    }
    return render(request, 'core/ranking.html', context)

def generate_test_view(request):
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        # Step 1: Extract text from the uploaded PDF
        pdf_file = request.FILES['pdf_file']
        with pdfplumber.open(pdf_file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()

        # Step 2: Detect the language of the text
        language = detect(text)

        # Step 3: Translate to Bulgarian if needed
        if language != "bg":
            translator = pipeline("translation", model="Helsinki-NLP/opus-mt-mul-bg")
            translated = translator(text, max_length=512)
            text = translated[0]['translation_text']

        # Step 4: Generate the test
        model_name = "gpt2"  # Replace with a larger model if needed
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

        # Step 5: Return the generated test
        return render(request, 'core/test_result.html', {'test': generated_test})

    return JsonResponse({'error': 'Invalid request method'}, status=405)
