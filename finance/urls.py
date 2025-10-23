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

    # Авторизация
    path('login/', auth_views.LoginView.as_view(template_name='finance/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
]
