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
from django.conf import settings
from django.db import connection
from django.http import HttpResponse
# Removed unused import
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
        pdf_file = request.FILES.get('pdf_file')
        start_page = int(request.POST.get('start_page', 1)) - 1
        end_page = int(request.POST.get('end_page', 1)) - 1
        due_date = request.POST.get('due_date')

        if not pdf_file:
            return render(request, 'core/test_creation.html', {'error': 'No file uploaded'})

        if pdf_file.size > MAX_FILE_SIZE:
            return render(request, 'core/test_creation.html', {'error': 'File size exceeds the maximum limit'})

        extracted_text = ""
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page_num in range(start_page, end_page + 1):
                    if 0 <= page_num < len(pdf.pages):
                        extracted_text += pdf.pages[page_num].extract_text() or ""
        except Exception as e:
            return render(request, 'core/test_creation.html', {'error': f'Error processing PDF: {str(e)}'})

        if not extracted_text.strip():
            return render(request, 'core/test_creation.html', {'error': 'No text found in the selected pages'})

        return render(request, 'core/test_creation.html', {
            'selected_text': extracted_text,
            'start_page': start_page + 1,
            'end_page': end_page + 1,
            'due_date': due_date,
        })

    return render(request, 'core/test_creation.html')


@csrf_exempt
def generate_test_view(request):
    if request.method == 'POST':
        try:
            # Parse the request data
            data = json.loads(request.body)
            pdf_file = request.FILES.get('pdf_file')
            selected_pages = data.get('selected_pages', [])
            due_date = data.get('due_date')

            # Validate due date
            if not parse_date(due_date):
                return JsonResponse({'error': 'Invalid due date format'}, status=400)

            # Validate file size
            if pdf_file.size > MAX_FILE_SIZE:
                return JsonResponse({'error': 'File size exceeds the maximum limit'}, status=400)

            # Extract text from selected pages using pdfplumber
            extracted_text = ""
            with pdfplumber.open(pdf_file) as pdf:
                for page_num in selected_pages:
                    if 0 <= page_num < len(pdf.pages):
                        extracted_text += pdf.pages[page_num].extract_text() or ""

            if not extracted_text.strip():
                return JsonResponse({'error': 'No text found in the selected pages'}, status=400)

            # Generate AI-based test using transformers
            tokenizer = AutoTokenizer.from_pretrained("gpt2")
            model = AutoModelForCausalLM.from_pretrained("gpt2")
            generator = pipeline('text-generation', model=model, tokenizer=tokenizer)

            prompt = f"Create a test based on the following content:\n{extracted_text}\n"
            ai_generated_test = generator(prompt, max_length=500, num_return_sequences=1)[0]['generated_text']

            # Save the test to the database (optional)
            Test.objects.create(content=ai_generated_test, due_date=due_date)

            return JsonResponse({'test': ai_generated_test}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

def run_sql_view(request):
    # Path to the SQL file
    script_path = os.path.join(settings.BASE_DIR, "core/sql/setup.sql")
    
    # Read the SQL file
    with open(script_path, "r") as file:
        sql_script = file.read()

    # Execute the SQL script
    with connection.cursor() as cursor:
        cursor.execute(sql_script)

    return HttpResponse("SQL script executed successfully!")
