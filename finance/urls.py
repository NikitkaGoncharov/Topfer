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

    # Транзакции
    path('transactions/', views.transactions, name='transactions'),
    path('transactions/add/', views.transaction_add, name='transaction_add'),
    path('transactions/<int:pk>/edit/', views.transaction_edit, name='transaction_edit'),
    path('transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),

    # Инвестиции (акции)
    path('investments/', views.investments, name='investments'),
    path('investments/add/', views.stock_add, name='stock_add'),
    path('investments/<int:pk>/edit/', views.stock_edit, name='stock_edit'),
    path('investments/<int:pk>/delete/', views.stock_delete, name='stock_delete'),

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
    path('api/stock/', views.get_stock_data, name='stock_data'),
    path('api/balance-history/', views.get_balance_history, name='balance_history'),
    path('api/comparison-data/', views.get_comparison_data, name='comparison_data'),

    # Авторизация
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
]
