from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from .models import Test, Subject, Question
from .forms import CustomUserCreationForm
import os
from django.utils.dateformat import format as date_format
import logging
import json
from datetime import date, timedelta
from django.views.decorators.csrf import csrf_exempt
from pdf2image import convert_from_path
from openai import OpenAI
from nltk.tokenize import sent_tokenize
import nltk
from concurrent.futures import ThreadPoolExecutor
import pytesseract
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
User = get_user_model()
from django.core.exceptions import ValidationError

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

# Initialize logger
logger = logging.getLogger(__name__) 

# OpenAI API Key
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENAI_API_KEY,
)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' 
@login_required
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
    return render(request, 'core/test_textbook.html', context, status=200)


@csrf_exempt
def test_question_view(request):
    """View to display the generated question."""
    question = request.session.get('generatedQuestion', None)

    if not question:
        return render(request, 'core/test_question.html', {'error': 'No question found. Please generate a test first.'}, status=404)

    return render(request, 'core/test_question.html', {'question': question}, status=200)
@login_required
def save_test_results(request):
    """Save test results to session."""
    results = request.POST.get('results') 
    request.session['results'] = results
    request.session.modified = True
    return JsonResponse({'status': 'Results saved successfully'}, status=200)
@login_required
def test_result_view(request):
    """View to display test results using session data or saved test questions, preserving streak logic."""
    if request.user.is_authenticated:
        profile = request.user.profile
        today = date.today()
        if profile.last_test_date is None:
            profile.streak = 1
        elif profile.last_test_date == today:
            pass
        elif (today - profile.last_test_date).days == 1:
            profile.streak += 1
        elif (today - profile.last_test_date).days > 1:
            profile.streak = 1
        else:
            profile.streak += 1

        profile.last_test_date = today
        profile.save()
    else:
        return render(request, 'core/test_result.html', {'error': 'User not authenticated.'}, status=401)

    results_json = request.session.get('results', None)
    if results_json:
        try:
            results = json.loads(results_json)
            total_questions = len(results)
            correct_answers = sum(1 for result in results if result['is_correct'])
            wrong_answers_count = total_questions - correct_answers
            
        except Exception:
            results = None
    else:
        results = None

    if not results:
        test = Test.objects.filter(user=request.user).order_by('-date').first()
        if not test:
            return render(request, 'core/test_result.html', {'error': 'No test found for user.'}, status=404)

        questions = Question.objects.filter(test=test)

        results = []
        correct_answers = 0
        for question in questions:
            selected_answer = None
            for item in test.question_data:
                if item.get('question') == question.question_text:
                    selected_answer = item.get('selected')
                    break

            is_correct = (selected_answer == question.correct_answer)
            if is_correct:
                correct_answers += 1

            results.append({
                'question': question.question_text,
                'selected': selected_answer,
                'correct': question.correct_answer,
                'is_correct': is_correct,
            })

        total_questions = len(results)
        wrong_answers_count = total_questions - correct_answers

    points = correct_answers * 3  - wrong_answers_count * 2

    profile = request.user.profile
    profile.points += points
    profile.save()
    

    context = {
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'wrong_answers_count': wrong_answers_count,
        'results': results,
        'streak': profile.streak,
        'points': points,
    }
    request.session['results'] = None 
    return render(request, 'core/test_result.html', context, status=200)

def save_points(request):
    """Save points to user profile."""
    if request.method == 'POST':
        data = json.loads(request.body)
        score = data.get('score', 0)
        profile = request.user.profile
        profile.points += score
        profile.save()
        return JsonResponse({'status': 'success', 'new_points': profile.points}, status=200)
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def profile_view(request):
    """View to display user profile and tests with optimized queries."""
    tests = Test.objects.select_related('subject').all()
    profile = request.user.profile
    profile_picture_url = profile.profile_picture.url if profile.profile_picture else f"{settings.MEDIA_URL}profile-picture/blank-profile-picture.jpg"
    context = {
        'username': request.user.username,
        'tests': tests,
        'streak': profile.streak if request.user.is_authenticated else 0,
        'profile_picture_url': profile_picture_url,
        'user': request.user,
        'profile': profile,
    }
    return render(request, 'core/profile.html', context, status=200)

@login_required
@require_POST
def upload_profile_picture(request):
    """Handle profile picture upload via AJAX."""
    if 'profile_picture' in request.FILES:
        profile = request.user.profile
        image = request.FILES['profile_picture']
        profile.profile_picture.save(image.name, image)
        profile.save()
        return JsonResponse({'status': 'success', 'profile_picture_url': profile.profile_picture.url}, status=200)
    else:
        return JsonResponse({'status': 'error', 'message': 'No image uploaded'}, status=400)


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
            return HttpResponse("<h1>Invalid username or password</h1>", status=401)

    def get_success_url(self):
        return '/dashboard/'


def signup_view(request):
    """View to handle user signup."""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            user.profile_picture = '/profile_pictures/blank-profile-picture.png'
            user.save()
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/signup.html', {'form': form}, status=200)


def home_view(request):
    """Home view."""
    return render(request, 'base.html', status=200)


@login_required
def dashboard_view(request):
    user = request.user
    today = date.today()

    upcoming_tests = Test.objects.filter(user=user, date__gte=today).order_by('date')

    if upcoming_tests.exists():
        next_test = upcoming_tests.first()
        
        display_date = next_test.date + timedelta(days=1)
        formatted_date = date_format(display_date, 'j F Y') 
        
        soonest_test = f"Test for {next_test.subject.name} on {formatted_date}"
        days_left = (display_date - today).days
    else:
        soonest_test = "No upcoming tests scheduled"
        days_left = "∞"


    
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
        cache.set('textbook_files', files, timeout=60 * 60)
    files = sorted(files, key=lambda x: x['name'])
    context = {
        'username': user.username,
        'soonest_test': soonest_test,
        'days_left': days_left,
        'streak': user.profile.streak if hasattr(user, 'profile') else 0,
        'is_first_login': user.last_login is None,
        'files': files,
        
    }

    return render(request, 'core/dashboard.html', context, status=200)

@login_required
def ranking_view(request):
    """View to display rankings."""
    if request.method == 'GET':
        top_users = User.objects.filter(profile__points__isnull=False).order_by('-profile__points')[:10]
        rankings = [
            {'username': user.username, 'score': user.profile.points}
            for user in top_users
        ]
        context = {
            'username': request.user.username,
            'rankings': rankings,
            'points': request.user.profile.points if request.user.is_authenticated else 0,
            'user': request.user, 
        }
        return render(request, 'core/ranking.html', context, status=200)

@login_required
@csrf_exempt
def generate_questions(request):
    """Generate questions with optimized text extraction and parallel processing."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)

    pdf_filename = None 
    pdf_file = None

    if request.content_type.startswith('multipart/form-data'):
        pdf_file = request.FILES.get('user_file', None)
        pdf_filename = request.POST.get('pdf_filename', None) 

        start_page = (
            request.POST.get('user_file_start_page') or
            request.POST.get('textbook_start_page')
        )
        end_page = (
            request.POST.get('user_file_end_page') or
            request.POST.get('textbook_end_page')
        )
        num_q = request.POST.get('num_q')

        if not start_page or not end_page or not num_q:
            return JsonResponse({'error': 'Missing start_page, end_page or num_q'}, status=400)

        try:
            start_page = int(start_page)
            end_page = int(end_page)
            num_q = int(num_q)
        except ValueError:
            return JsonResponse({'error': 'Invalid start_page, end_page or num_q'}, status=400)

        if pdf_file:
            temp_path = os.path.join(settings.MEDIA_ROOT, pdf_file.name)
            with open(temp_path, 'wb+') as destination:
                for chunk in pdf_file.chunks():
                    destination.write(chunk)
            pdf_path = temp_path
        elif pdf_filename:
            pdf_path = os.path.join(settings.MEDIA_ROOT, os.path.basename(pdf_filename))
            if not os.path.exists(pdf_path):
                return JsonResponse({'error': 'PDF file not found'}, status=404)
        else:
            return JsonResponse({'error': 'No PDF file provided'}, status=400)
    else:
        try:
            data = json.loads(request.body)
            pdf_filename = data.get('pdf_filename')
            start_page = int(data.get('start_page'))
            end_page = int(data.get('end_page'))
            num_q = int(data.get('num_q'))
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
        gray_image = img.convert('L') 
        return pytesseract.image_to_string(gray_image, lang='bul+eng')

    with ThreadPoolExecutor() as executor:
        results = executor.map(process_page, images)

    
    extracted_text = '\n'.join(results)

    def truncate_text(text, num_questions, sentences_per_question=5):
        sentences = sent_tokenize(text)
        needed_sentences = num_questions * sentences_per_question
        return ' '.join(sentences[:needed_sentences])
    
    if len(extracted_text) < 1000:
        num_q = 2
    elif len(extracted_text) < 2000:
        num_q = 3

    prompt = (
        f"Прочети следния текст и създай ТОЧНО {num_q} въпроса на БЪЛГАРСКИ език с 4 възможни отговора (А, Б, В, Г), като само един от тях е правилен.\n\n"
        "Използвай САМО информация, която се съдържа директно в текста. НЕ използвай външни източници и НЕ добавяй никакви предположения.\n"
        "Ако даден факт не е изрично споменат в текста, НЕ създавай въпрос по него!\n\n"
        "Форматът трябва да бъде точно както следва (спазвай разстоянията и новите редове):\n\n"
        "Въпрос: Кой е създателят на теорията на относителността?\n"
        "А) Исак Нютон\n"
        "Б) Никола Тесла\n"
        "В) Алберт Айнщайн\n"
        "Г) Галилео Галилей\n"
        "Правилен отговор: В\n\n"
        f"Генерирай въпросите точно в този формат.\n\n"
        f"Текст за въпроси:\n{truncate_text(extracted_text, num_q)}"
    )

    try:
        response = client.chat.completions.create(
            model= "google/gemini-2.0-flash-exp:free",
            messages=[{"role": "user", "content": prompt}],
        )
        result = response.choices[0].message.content.strip() 
        print(result)
    except Exception as e:
        return JsonResponse({'error': f'OpenAI API error: {str(e)}'}, status=500) 
    return JsonResponse({'question': result}, status=200) 

@login_required
@csrf_exempt 
def save_subject(request):
    if request.method == 'POST':
        try:
            logger.debug("save_subject view called")
            data = json.loads(request.body)
            logger.debug(f"Request body: {data}")
            date = data.get('date')
            subject_name = data.get('subject')

            if not date or not subject_name:
                logger.warning("Missing date or subject")
                return JsonResponse({'error': 'Missing date or subject'}, status=400)
            try:
                subject = Subject.objects.get(name=subject_name)
                logger.debug(f"Found subject: {subject}")
            except Subject.DoesNotExist:
                logger.warning(f"Subject not found: {subject_name}")
                return JsonResponse({'error': 'Subject not found'}, status=400)

            try:
                test = Test.objects.create(
                    user=request.user,
                    date=date,
                    subject=subject,  
                    grade=0,  
                    question_data=[]  
                )
                logger.info(f"Test created: {test}")
                return JsonResponse({'date': test.date, 'subject': test.subject.name}, status=201)

            except Exception as e:
                logger.error(f"Error creating test: {str(e)}")
                return JsonResponse({'error': str(e)}, status=400)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {str(e)}")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            
            logger.error(f"Error saving test: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def saved_tests(request):
    logger.debug("saved_tests view called") 
    user = request.user
    month = request.GET.get('month')
    year = request.GET.get('year')

    if not month or not year:
        logger.warning("Month or year missing")
        return JsonResponse({'error': 'Month and year are required'}, status=400)

    try:
        month = int(month)
        year = int(year)

    except Exception as e:
        logger.exception("Invalid month or year") 
        return JsonResponse({'error': 'INVALID MONTH OR YEAR'}, status=400)

    try:
        tests = Test.objects.filter(user=user, date__month=month, date__year=year).order_by('-date')
        tests_data = []
        for test in tests:
            subject_name = test.subject.name if test.subject else "No Subject" 
            tests_data.append({
                'subject': subject_name,
                'date': test.date.strftime('%Y-%m-%d'),
            })

        return JsonResponse({'tests': tests_data}, status=200)
    except Exception as e:
        logger.exception("Error processing tests")
        return JsonResponse({'error': str(e)}, status=500) 

@csrf_exempt
def change_password(request):
    """View to handle password change."""
    if request.method == 'PUT':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'User is not authenticated'}, status=401)

        try:
            data = json.loads(request.body)
            new_password = data.get('new_password')
            confirm_password = data.get('confirm_password')
        except Exception:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        if new_password != confirm_password:
            return JsonResponse({'error': 'Passwords do not match'}, status=400)

        if len(new_password) < 8:
            return JsonResponse({'error': 'Password too short. Minimum length is 8 characters.'}, status=400)

        user = request.user
        user.set_password(new_password)
        user.save()

        update_session_auth_hash(request, user) 

        return JsonResponse({'success': True, 'redirect_url': '/profile/'}, status=200)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def change_username(request):
    """View to handle username change."""
    if request.method == 'PUT':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'User is not authenticated'}, status=401)

        try:
            data = json.loads(request.body)
            logger.debug(f"change_username received data: {data}")
            new_username = data.get('new_username')
            logger.debug(f"new_username: {new_username}")

            if User.objects.filter(username=new_username).exists():
                return JsonResponse({'error': 'Username already exists'}, status=400)

            if len(new_username) < 5: 
                return JsonResponse({'error': 'Username is too short. Minimum length is 5 characters.'}, status=400)

            if not new_username.isalnum():
                return JsonResponse({'error': 'Username can only contain letters and numbers.'}, status=400)

            user = request.user
            user.username = new_username
            user.save()
            return JsonResponse({'success': True, 'redirect_url': '/profile/'}, status=200)

        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error in change_username: {str(e)}")
            return JsonResponse({'error': 'Internal server error'}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def change_name(request):
    """View to handle name change."""
    if request.method == 'PUT':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'User is not authenticated'}, status=401)

        try:
            data = json.loads(request.body)
            new_name = data.get('new_name')
        except Exception:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        if not new_name:
            return JsonResponse({'error': 'Name cannot be empty'}, status=400)

        try:
            first_name, last_name = new_name.split(' ', 1) 
        except ValueError:
            return JsonResponse({'error': 'Please provide both first and last name'}, status=400)

        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.save()

       
        return JsonResponse({'success': True, 'redirect_url': '/profile/'}, status=200)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def delete_account(request):
    """View to handle account deletion."""
    if request.method == 'DELETE':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'User is not authenticated'}, status=401)
        try:
            user = request.user
            user.delete()
            return JsonResponse({'success': True, 'redirect_url': '/'})
        except Exception as e:
            logger.error(f"Error deleting account: {str(e)}")
            return JsonResponse({'error': 'Internal server error'}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def learn(request):
    """View to summarize the textbook so you can learn"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)

    pdf_filename = None 
    pdf_file = None

    if request.content_type.startswith('multipart/form-data'):
        pdf_file = request.FILES.get('user_file', None)
        pdf_filename = request.POST.get('pdf_filename', None) 

        start_page = (
            request.POST.get('user_file_start_page') or
            request.POST.get('textbook_start_page')
        )
        end_page = (
            request.POST.get('user_file_end_page') or
            request.POST.get('textbook_end_page')
        )

        if not start_page or not end_page:
            return JsonResponse({'error': 'Missing start_page, end_page'}, status=400)

        try:
            start_page = int(start_page)
            end_page = int(end_page)
        except ValueError:
            return JsonResponse({'error': 'Invalid start_page, end_page'}, status=400)

        if pdf_file:
            temp_path = os.path.join(settings.MEDIA_ROOT, pdf_file.name)
            with open(temp_path, 'wb+') as destination:
                for chunk in pdf_file.chunks():
                    destination.write(chunk)
            pdf_path = temp_path
        elif pdf_filename:
            pdf_path = os.path.join(settings.MEDIA_ROOT, os.path.basename(pdf_filename))
            if not os.path.exists(pdf_path):
                return JsonResponse({'error': 'PDF file not found'}, status=404)
        else:
            return JsonResponse({'error': 'No PDF file provided'}, status=400)
    else:
        try:
            data = json.loads(request.body)
            pdf_filename = data.get('pdf_filename')
            start_page = int(data.get('start_page'))
            end_page = int(data.get('end_page'))
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
        gray_image = img.convert('L') 
        return pytesseract.image_to_string(gray_image, lang='bul+eng')

    with ThreadPoolExecutor() as executor:
        results = executor.map(process_page, images)

    
    extracted_text = '\n'.join(results)

    prompt = (
        "Прочети следния текст и го обясни ясно на БЪЛГАРСКИ език, като използваш различни символи и емотикони за различни секции и теми, подобно на ChatGPT. Не слагай допълнителни space-ове и не използвай съкращения от типа BG  за България\n"
        "Използвай подходящи символи за заглавия (например: 📚, 📝, 🔬, 💡), за важни точки (например: ⭐, ➡️, ✔️), за примери (например: 🧩, 📝), и за обобщения (например: 🏁, 📌).\n"
        "Направи текста интересен и лесен за учене, като структурираш материала на секции с подходящи емотикони и символи. Накрая направи обобщение като използваш тези символи (например: 🏁, 📌).\n"
        "Не добавяй информация, която не е в текста. Не слагай начални изречрния като тези 'Ето структурирано обяснение на текста, като използвам символи и емотикони, за да е по-интересно и лесно за усвояване:'\n\n"
        f"Текст за обобщение:\n{extracted_text}"
    )

    try:
        response = client.chat.completions.create(
            model= "google/gemini-2.0-flash-exp:free",
            messages=[{"role": "user", "content": prompt}],
        )
        result = response.choices[0].message.content.strip() 
        print(result)
    except Exception as e:
        return JsonResponse({'error': f'OpenAI API error: {str(e)}'}, status=500) 
    request.session['generatedSummary'] = result
    return JsonResponse({'summary': result}, status=200) 
@csrf_exempt
def summarize_text(request):
    """View to display the generated summary."""
    summary = request.session.get('generatedSummary', None)

    if not summary:
        return render(request, 'core/summarize.html', {'error': 'No summary found. Please generate a summary first.'}, status=404)

    return render(request, 'core/summarize.html', {'summary': summary}, status=200)