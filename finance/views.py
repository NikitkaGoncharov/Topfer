from django.shortcuts import render
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from .models import User, Account, Transaction, Category, Budget, Tag


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
