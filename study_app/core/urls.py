from django.urls import path
from .views import home_view, login_view, signup_view, dashboard_view, profile_view, test_creation_view, test_list_view, ranking_view, generate_test_view

urlpatterns = [
    path('', home_view, name='home'),
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('profile/', profile_view, name='profile'),
    path('test-creation/', test_creation_view, name='test_creation'),
    path('test-list/', test_list_view, name='test_list'),
    path('ranking/', ranking_view, name='ranking'),
    path('generate-test/', generate_test_view, name='generate_test'),
]