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
import torch.nn as nn

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


def test_creation_view(request):
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        try:
            # Step 1: Extract form data
            pdf_file = request.FILES['pdf_file']
            start_page = int(request.POST.get('start_page'))
            end_page = int(request.POST.get('end_page'))
            due_date = request.POST.get('due_date')

            # Step 2: Extract text from the specified pages of the PDF
            with pdfplumber.open(pdf_file) as pdf:
                if start_page < 1 or end_page > len(pdf.pages) or start_page > end_page:
                    raise ValidationError("Invalid page range.")
                text = ""
                for page_num in range(start_page - 1, end_page):
                    text += pdf.pages[page_num].extract_text()

            # Step 3: Detect the language of the text
            language = detect(text)

            # Step 4: Translate to Bulgarian if needed
            if language != "bg":
                translator = pipeline("translation", model="Helsinki-NLP/opus-mt-mul-bg")
                translated = translator(text, max_length=512)
                text = translated[0]['translation_text']

            # Step 5: Generate the test
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
            outputs = model.generate(inputs, max_length=1024, num_return_sequences=1, temperature=0.7)
            generated_test = tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Step 6: Render the result
            return render(request, 'core/test_creation.html', {
                'selected_text': text,
                'start_page': start_page,
                'end_page': end_page,
                'due_date': due_date,
                'generated_test': generated_test
            })

        except Exception as e:
            return render(request, 'core/test_creation.html', {'error': f"Error: {str(e)}"})

    return render(request, 'core/test_creation.html')


def test_list_view(request):
    # Example context data for the test list page
    context = {
        'tests': [
            {'name': 'Math Test', 'date': '2025-03-20'},
            {'name': 'Science Test', 'date': '2025-03-19'},
            {'name': 'History Test', 'date': '2025-03-18'},
        ]
    }
    return render(request, 'core/test_list.html', context)

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
        {text[:1000]}  # Limit the content to 1000 characters

        Provide the test in Bulgarian.
        """
        inputs = tokenizer.encode(prompt, return_tensors="pt", truncation=True, max_length=1024)

        try:
            outputs = model.generate(
                inputs, 
                max_new_tokens=500,  # Limit the number of new tokens generated
                num_return_sequences=1, 
                temperature=0.7,
                do_sample=True,
                top_k=50,
                top_p=0.95,
            )
            generated_test = tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Step 5: Return the generated test
            return render(request, 'core/test_result.html', {'test': generated_test})
        except Exception as e:
            return render(request, 'core/test_creation.html', {'error': f"Error generating test: {str(e)}"})

    return render(request, 'core/test_creation.html')
