from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    home_view, CustomLoginView, signup_view, dashboard_view, profile_view,
    test_creation_view, test_list_view, ranking_view, generate_test_view,
    take_test_view, test_create_view, test_grade_view, test_textbook_view,
    test_subject_view, test_result_view, test_question_view, test_pages_daysleft_view
)

urlpatterns = [
    path('', home_view, name='home'),
    path('signup/', signup_view, name='signup'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('profile/', profile_view, name='profile'),
    path('test-list/', test_list_view, name='test_list'),
    path('ranking/', ranking_view, name='ranking'),
    path('generate-test/', generate_test_view, name='generate_test'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('take-test/<int:test_id>/', take_test_view, name='take_test'),
    path('test-create/', test_create_view, name='test_create'),
    path('test-grade/', test_grade_view, name='test_grade'),
    path('test-textbook/', test_textbook_view, name='test_textbook'),
    path('test-subject/', test_subject_view, name='test_subject'),
    path('test-result/', test_result_view, name='test_result'),
    path('test-creation/', test_creation_view, name='test_creation'),
    path('test-question/', test_question_view, name='test_question'),
    path('test-pages-daysleft/', test_pages_daysleft_view, name='test_pages_daysleft'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)