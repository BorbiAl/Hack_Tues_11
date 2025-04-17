from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    home_view, CustomLoginView, signup_view, dashboard_view, profile_view,
    test_creation_view, ranking_view, test_textbook_view,
    test_result_view, test_question_view
)

urlpatterns = [
    path('', home_view, name='home'),
    path('signup/', signup_view, name='signup'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('profile/', profile_view, name='profile'),
    path('ranking/', ranking_view, name='ranking'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('test-textbook/', test_textbook_view, name='test_textbook'),
    path('test-result/', test_result_view, name='test_result'),
    path('test-creation/', test_creation_view, name='test_creation'),
    path('test-question/', test_question_view, name='test_question'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)