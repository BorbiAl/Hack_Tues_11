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
    path('save-subject/', views.save_subject, name='save_subject'),
    path('saved-tests/', views.saved_tests, name='saved_tests'),
    path('change-password/', views.change_password, name='change_password'),
    path('change-name/', views.change_name, name='change_name'),
    path('change-username/', views.change_username, name='change_username'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('save-points/', views.save_points, name='save_points'),
    path('upload-profile-picture/', views.upload_profile_picture, name='upload_profile_picture'),
    path('learn/', views.learn, name='learn'),
]
 
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)