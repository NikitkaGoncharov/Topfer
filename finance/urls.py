from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'finance'

urlpatterns = [
    # Главная страница
    path('', views.index, name='index'),

    # Страницы разделов
    path('accounts/', views.accounts, name='accounts'),
    path('accounts/add/', views.account_add, name='account_add'),
    path('accounts/<int:pk>/edit/', views.account_edit, name='account_edit'),
    path('accounts/<int:pk>/delete/', views.account_delete, name='account_delete'),
    path('transactions/', views.transactions, name='transactions'),
    path('investments/', views.investments, name='investments'),
    path('analytics/', views.analytics, name='analytics'),

    # Бюджеты
    path('budgets/', views.budgets, name='budgets'),
    path('budgets/add/', views.budget_add, name='budget_add'),
    path('budgets/<int:pk>/edit/', views.budget_edit, name='budget_edit'),
    path('budgets/<int:pk>/delete/', views.budget_delete, name='budget_delete'),

    # Поиск
    path('search/', views.search, name='search'),

    # API endpoints
    path('api/crypto/', views.get_crypto_data, name='crypto_data'),

    # Авторизация
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
]
