from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('ranking/', views.ranking_view, name='ranking'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('test-textbook/', views.test_textbook_view, name='test_textbook'),
    path('test-result/', views.test_result_view, name='test_result'),
    path('test-question/', views.test_question_view, name='test_question'),
    path('generate-questions/', views.generate_questions, name='generate_questions'),
    path('api/saved-tests/', views.SavedTestsView.as_view(), name='saved_tests'),
    path('api/save-test/', views.SaveTestView.as_view(), name='save_test'),
]
 
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)