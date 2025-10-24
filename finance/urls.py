from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'finance'

urlpatterns = [
    # Главная страница
    path('', views.index, name='index'),

    # Страницы разделов
    path('accounts/', views.accounts, name='accounts'),
    path('transactions/', views.transactions, name='transactions'),
    path('investments/', views.investments, name='investments'),
    path('analytics/', views.analytics, name='analytics'),

    # Поиск
    path('search/', views.search, name='search'),

    # API endpoints
    path('api/crypto/', views.get_crypto_data, name='crypto_data'),

    # Авторизация
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
]
