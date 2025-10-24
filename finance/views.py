from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import timedelta
from .models import User, Account, Transaction, Category, Budget, Tag
from .services import BinanceService
from .forms import UserRegistrationForm, UserLoginForm


def index(request):
    """
    Главная страница с виджетами:
    1. Финансовый обзор - общая сумма по всем счетам (агрегатная функция SUM)
    2. Топ категорий расходов - популярные категории (агрегатная функция COUNT)
    3. Последние транзакции - топ-5 последних транзакций (order_by)
    4. Популярные счета - счета с наибольшим балансом (order_by)
    5. Активные бюджеты - текущие активные бюджеты (filter)
    """

    # Виджет 1: Финансовый обзор - общая сумма по всем счетам
    # QuerySet: aggregate(Sum()) - агрегатная функция суммирования
    total_balance = Account.objects.aggregate(
        total=Sum('balance')
    )['total'] or 0

    # Количество счетов
    # QuerySet: count() - агрегатная функция подсчета
    accounts_count = Account.objects.count()

    # Количество транзакций
    # QuerySet: count() - агрегатная функция подсчета
    transactions_count = Transaction.objects.count()

    # Виджет 2: Топ-5 категорий по количеству транзакций
    # QuerySet: filter() - фильтрация по типу расходов
    # annotate(Count()) - агрегатная функция подсчета
    # order_by() - сортировка по убыванию количества
    # [:5] - ограничение до 5 записей
    top_expense_categories = Category.objects.filter(
        category_type='expense'
    ).annotate(
        transaction_count=Count('transactions')
    ).order_by('-transaction_count')[:5]

    # Виджет 3: Последние 10 транзакций
    # QuerySet: all() - все записи
    # order_by() - сортировка по дате (от новых к старым)
    # select_related() - оптимизация запросов
    # [:10] - ограничение до 10 записей
    recent_transactions = Transaction.objects.all().select_related(
        'account', 'category', 'account__currency'
    ).order_by('-transaction_date')[:10]

    # Виджет 4: Популярные счета (топ-5 по балансу)
    # QuerySet: order_by() - сортировка по балансу (от большего к меньшему)
    # select_related() - оптимизация запросов
    # [:5] - ограничение до 5 записей
    popular_accounts = Account.objects.all().select_related(
        'currency', 'user'
    ).order_by('-balance')[:5]

    # Виджет 5: Активные бюджеты
    # QuerySet: filter() - фильтрация по датам
    # Q объекты для сложных условий
    today = timezone.now().date()
    active_budgets = Budget.objects.filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today),
        start_date__lte=today
    ).select_related('user', 'category')[:5]

    # Статистика за последний месяц
    last_month = timezone.now() - timedelta(days=30)

    # Сумма доходов за месяц
    # QuerySet: filter() - фильтрация по типу и дате
    # aggregate(Sum()) - агрегатная функция суммирования
    monthly_income = Transaction.objects.filter(
        transaction_type='income',
        transaction_date__gte=last_month
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Сумма расходов за месяц
    # QuerySet: filter() - фильтрация по типу и дате
    # exclude() - исключение определенных записей
    # aggregate(Sum()) - агрегатная функция суммирования
    monthly_expense = Transaction.objects.filter(
        transaction_type='expense',
        transaction_date__gte=last_month
    ).exclude(
        category__isnull=True
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'total_balance': total_balance,
        'accounts_count': accounts_count,
        'transactions_count': transactions_count,
        'top_expense_categories': top_expense_categories,
        'recent_transactions': recent_transactions,
        'popular_accounts': popular_accounts,
        'active_budgets': active_budgets,
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
    }

    return render(request, 'finance/index.html', context)


def accounts(request):
    """Страница со всеми счетами"""
    all_accounts = Account.objects.all().select_related('currency', 'user').order_by('-created_date')

    context = {
        'accounts': all_accounts,
    }

    return render(request, 'finance/accounts.html', context)


def transactions(request):
    """Страница со всеми транзакциями"""
    all_transactions = Transaction.objects.all().select_related(
        'account', 'category', 'account__currency'
    ).prefetch_related('tags').order_by('-transaction_date')

    context = {
        'transactions': all_transactions,
    }

    return render(request, 'finance/transactions.html', context)


def investments(request):
    """Страница инвестиций"""
    # Счета типа investment
    investment_accounts = Account.objects.filter(
        account_type='investment'
    ).select_related('currency', 'user').order_by('-balance')

    context = {
        'investment_accounts': investment_accounts,
    }

    return render(request, 'finance/investments.html', context)


def analytics(request):
    """Страница аналитики"""
    # Статистика по категориям
    expense_by_category = Category.objects.filter(
        category_type='expense'
    ).annotate(
        total_amount=Sum('transactions__amount'),
        count=Count('transactions')
    ).order_by('-total_amount')

    income_by_category = Category.objects.filter(
        category_type='income'
    ).annotate(
        total_amount=Sum('transactions__amount'),
        count=Count('transactions')
    ).order_by('-total_amount')

    context = {
        'expense_by_category': expense_by_category,
        'income_by_category': income_by_category,
    }

    return render(request, 'finance/analytics.html', context)


def search(request):
    """
    Функция поиска по транзакциям
    Поиск выполняется по описанию транзакции и названию категории
    """
    query = request.GET.get('q', '')
    results = []

    if query:
        # QuerySet: filter() с Q объектами для поиска по нескольким полям
        # icontains - регистронезависимый поиск подстроки
        # distinct() - убирает дубликаты
        results = Transaction.objects.filter(
            Q(description__icontains=query) |
            Q(category__category_name__icontains=query) |
            Q(account__account_name__icontains=query)
        ).select_related(
            'account', 'category', 'account__currency'
        ).distinct().order_by('-transaction_date')[:20]

    context = {
        'query': query,
        'results': results,
    }

    return render(request, 'finance/search.html', context)


def get_crypto_data(request):
    """
    AJAX endpoint для получения данных о криптовалютах с Binance
    Возвращает топ-5 криптовалют по объему торгов

    Returns:
        JsonResponse: JSON с данными о криптовалютах
    """
    try:
        limit = int(request.GET.get('limit', 5))
        cryptos = BinanceService.get_top_cryptos(limit=limit)

        return JsonResponse({
            'success': True,
            'data': cryptos
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def register(request):
    """
    Обрабатывает регистрацию нового пользователя

    GET: Отображает форму регистрации
    POST: Создает нового пользователя и автоматически авторизует его

    Returns:
        HttpResponse: Страница регистрации или редирект на главную
    """
    if request.user.is_authenticated:
        return redirect('finance:index')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт для {username} успешно создан! Вы автоматически вошли в систему.')
            login(request, user)
            return redirect('finance:index')
    else:
        form = UserRegistrationForm()

    return render(request, 'finance/register.html', {'form': form})


def user_login(request):
    """
    Обрабатывает вход пользователя в систему

    GET: Отображает форму входа
    POST: Аутентифицирует пользователя

    Returns:
        HttpResponse: Страница входа или редирект на главную
    """
    if request.user.is_authenticated:
        return redirect('finance:index')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {username}!')
                return redirect('finance:index')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    else:
        form = UserLoginForm()

    return render(request, 'finance/login.html', {'form': form})


def user_logout(request):
    """
    Выход пользователя из системы

    Returns:
        HttpResponse: Редирект на главную страницу
    """
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы')
    return redirect('finance:index')
