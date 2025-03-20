from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('test-creation/', views.test_creation_view, name='test_creation'),
    path('test-list/', views.test_list_view, name='test_list'),
    path('ranking/', views.ranking_view, name='ranking'),
]