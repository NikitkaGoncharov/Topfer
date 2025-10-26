from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import timedelta
import json
from .models import User, Account, Transaction, Category, Budget, Tag, Stock
from .services import BinanceService, StockService
from .forms import UserRegistrationForm, UserLoginForm, AccountForm, BudgetForm, TransactionForm, StockForm


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
    """
    Страница со счетами текущего пользователя
    Отображает все счета с группировкой по типам и общей статистикой
    """
    if request.user.is_authenticated:
        user_accounts = Account.objects.filter(user=request.user).select_related('currency').order_by('-created_date')

        # Статистика по счетам
        total_balance = user_accounts.aggregate(total=Sum('balance'))['total'] or 0
        accounts_by_type = {}
        for account in user_accounts:
            acc_type = account.get_account_type_display()
            if acc_type not in accounts_by_type:
                accounts_by_type[acc_type] = []
            accounts_by_type[acc_type].append(account)
    else:
        user_accounts = Account.objects.none()
        total_balance = 0
        accounts_by_type = {}

    context = {
        'user_accounts': user_accounts,
        'accounts_by_type': accounts_by_type,
        'total_balance': total_balance,
        'accounts_count': user_accounts.count(),
    }

    return render(request, 'finance/accounts.html', context)


def transactions(request):
    """Страница со всеми транзакциями с фильтрами и пагинацией"""
    # Проверяем, авторизован ли пользователь
    if request.user.is_authenticated:
        # Получаем транзакции пользователя
        all_transactions = Transaction.objects.filter(
            account__user=request.user
        ).select_related(
            'account', 'category', 'account__currency'
        ).prefetch_related('tags').order_by('-transaction_date')

        user_accounts = Account.objects.filter(user=request.user)
    else:
        # Для неавторизованных пользователей - пустой queryset
        all_transactions = Transaction.objects.none()
        user_accounts = Account.objects.none()

    # Фильтры (только для авторизованных пользователей)
    transaction_type = request.GET.get('type', '')
    category_id = request.GET.get('category', '')
    account_id = request.GET.get('account', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if request.user.is_authenticated:
        if transaction_type:
            all_transactions = all_transactions.filter(transaction_type=transaction_type)

        if category_id:
            all_transactions = all_transactions.filter(category_id=category_id)

        if account_id:
            all_transactions = all_transactions.filter(account_id=account_id)

        if date_from:
            all_transactions = all_transactions.filter(transaction_date__gte=date_from)

        if date_to:
            all_transactions = all_transactions.filter(transaction_date__lte=date_to)

    # Пагинация - 10 транзакций на страницу
    paginator = Paginator(all_transactions, 10)
    page = request.GET.get('page')

    try:
        transactions_page = paginator.page(page)
    except PageNotAnInteger:
        # Если номер страницы не целое число, показываем первую страницу
        transactions_page = paginator.page(1)
    except EmptyPage:
        # Если страница вне диапазона, показываем последнюю страницу
        transactions_page = paginator.page(paginator.num_pages)

    # Получаем все категории для фильтров
    categories = Category.objects.all()

    context = {
        'transactions': transactions_page,
        'categories': categories,
        'user_accounts': user_accounts,
        'selected_type': transaction_type,
        'selected_category': category_id,
        'selected_account': account_id,
        'date_from': date_from,
        'date_to': date_to,
    }

    return render(request, 'finance/transactions.html', context)


@login_required
def transaction_add(request):
    """Добавление новой транзакции"""
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save()
            messages.success(request, f'Транзакция на сумму {transaction.amount} {transaction.account.currency.symbol} успешно создана!')
            return redirect('finance:transactions')
    else:
        form = TransactionForm(user=request.user)

    return render(request, 'finance/transaction_form.html', {
        'form': form,
        'title': 'Добавить транзакцию'
    })


@login_required
def transaction_edit(request, pk):
    """Редактирование транзакции"""
    transaction = get_object_or_404(Transaction, pk=pk, account__user=request.user)

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction, user=request.user)
        if form.is_valid():
            transaction = form.save()
            messages.success(request, 'Транзакция успешно обновлена!')
            return redirect('finance:transactions')
    else:
        form = TransactionForm(instance=transaction, user=request.user)

    return render(request, 'finance/transaction_form.html', {
        'form': form,
        'title': 'Редактировать транзакцию',
        'transaction': transaction
    })


@login_required
def transaction_delete(request, pk):
    """Удаление транзакции"""
    transaction = get_object_or_404(Transaction, pk=pk, account__user=request.user)

    if request.method == 'POST':
        messages.success(request, f'Транзакция на сумму {transaction.amount} {transaction.account.currency.symbol} успешно удалена!')
        transaction.delete()
        return redirect('finance:transactions')

    return render(request, 'finance/transaction_confirm_delete.html', {
        'transaction': transaction
    })


def investments(request):
    """Страница инвестиций с портфелем акций"""
    if not request.user.is_authenticated:
        # Для неавторизованных пользователей
        context = {
            'stocks_data': [],
            'stocks_count': 0,
            'total_investment': 0,
            'total_current_value': 0,
            'total_profit': 0,
            'total_profit_percent': 0,
        }
        return render(request, 'finance/investments.html', context)

    # Получаем все акции пользователя
    user_stocks = Stock.objects.filter(user=request.user).select_related('currency').order_by('-purchase_date')

    # Собираем данные по каждой акции с текущими ценами
    stocks_data = []
    total_investment = 0
    total_current_value = 0

    for stock in user_stocks:
        # Получаем текущую цену акции
        current_price_data = StockService.get_stock_price(stock.ticker)

        if current_price_data:
            current_price = current_price_data['price']

            # Рассчитываем прибыль/убыток
            profit_data = StockService.calculate_profit(
                stock.purchase_price,
                current_price,
                stock.quantity
            )

            stocks_data.append({
                'stock': stock,
                'current_price': current_price,
                'current_price_data': current_price_data,
                'profit_data': profit_data,
            })

            total_investment += profit_data['total_investment']
            total_current_value += profit_data['current_value']
        else:
            # Если не удалось получить цену, показываем базовую информацию
            stocks_data.append({
                'stock': stock,
                'current_price': None,
                'current_price_data': None,
                'profit_data': {
                    'total_investment': float(stock.total_investment),
                    'current_value': None,
                    'profit': None,
                    'profit_percent': None,
                },
            })
            total_investment += float(stock.total_investment)

    # Рассчитываем общую прибыль портфеля
    total_profit = total_current_value - total_investment
    total_profit_percent = (total_profit / total_investment * 100) if total_investment > 0 else 0

    context = {
        'stocks_data': stocks_data,
        'stocks_count': user_stocks.count(),
        'total_investment': total_investment,
        'total_current_value': total_current_value,
        'total_profit': total_profit,
        'total_profit_percent': total_profit_percent,
    }

    return render(request, 'finance/investments.html', context)


def calculate_balance_history(user, days):
    """
    Вспомогательная функция для расчета истории баланса за указанный период
    """
    from datetime import date, timedelta
    from collections import defaultdict

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Получаем начальный баланс (сумма всех транзакций до start_date)
    initial_transactions = Transaction.objects.filter(
        account__user=user,
        transaction_date__lt=start_date
    )

    initial_balance = 0
    for trans in initial_transactions:
        if trans.transaction_type == 'income':
            initial_balance += float(trans.amount)
        elif trans.transaction_type == 'expense':
            initial_balance -= float(trans.amount)

    # Получаем транзакции за период
    period_transactions = Transaction.objects.filter(
        account__user=user,
        transaction_date__gte=start_date,
        transaction_date__lte=end_date
    ).order_by('transaction_date')

    # Группируем транзакции по дням
    daily_changes = defaultdict(float)
    for trans in period_transactions:
        trans_date = trans.transaction_date.date()
        if trans.transaction_type == 'income':
            daily_changes[trans_date] += float(trans.amount)
        elif trans.transaction_type == 'expense':
            daily_changes[trans_date] -= float(trans.amount)

    # Создаем массивы для графика
    balance_labels = []
    balance_data = []
    current_balance = initial_balance

    # Определяем формат даты в зависимости от периода
    if days <= 30:
        date_format = '%d.%m'
    elif days <= 90:
        date_format = '%d.%m'
    else:
        date_format = '%d.%m.%y'

    # Проходим по всем дням периода
    current_date = start_date
    while current_date <= end_date:
        balance_labels.append(current_date.strftime(date_format))
        current_balance += daily_changes.get(current_date, 0)
        balance_data.append(round(current_balance, 2))
        current_date += timedelta(days=1)

    return {
        'labels': balance_labels,
        'data': balance_data
    }


def calculate_comparison_data(user, days=None):
    """
    Вспомогательная функция для расчета данных сравнения доходов и расходов по категориям
    days=None означает "все время"
    """
    from datetime import date, timedelta
    from django.db.models import Sum, Q

    # Определяем период
    if days:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        date_filter = Q(transactions__transaction_date__gte=start_date, transactions__transaction_date__lte=end_date)
    else:
        date_filter = Q()  # Пустой фильтр = все время

    # Получаем расходы по категориям
    expense_by_category = Category.objects.filter(
        category_type='expense'
    ).annotate(
        total=Sum('transactions__amount', filter=Q(transactions__account__user=user) & date_filter)
    ).order_by('-total')

    # Получаем доходы по категориям
    income_by_category = Category.objects.filter(
        category_type='income'
    ).annotate(
        total=Sum('transactions__amount', filter=Q(transactions__account__user=user) & date_filter)
    ).order_by('-total')

    # Собираем все уникальные категории
    all_categories = set()
    expense_dict = {}
    income_dict = {}

    for cat in expense_by_category:
        if cat.total and cat.total > 0:
            all_categories.add(cat.category_name)
            expense_dict[cat.category_name] = float(cat.total)

    for cat in income_by_category:
        if cat.total and cat.total > 0:
            all_categories.add(cat.category_name)
            income_dict[cat.category_name] = float(cat.total)

    # Сортируем категории по алфавиту
    sorted_categories = sorted(all_categories)

    return {
        'labels': sorted_categories,
        'expenses': [expense_dict.get(cat, 0) for cat in sorted_categories],
        'incomes': [income_dict.get(cat, 0) for cat in sorted_categories]
    }


def analytics(request):
    """Страница аналитики"""
    # Проверяем авторизацию пользователя
    if request.user.is_authenticated:
        # Статистика по категориям только для текущего пользователя
        expense_by_category = Category.objects.filter(
            category_type='expense'
        ).annotate(
            total_amount=Sum('transactions__amount', filter=Q(transactions__account__user=request.user)),
            count=Count('transactions', filter=Q(transactions__account__user=request.user))
        ).order_by('-total_amount')

        income_by_category = Category.objects.filter(
            category_type='income'
        ).annotate(
            total_amount=Sum('transactions__amount', filter=Q(transactions__account__user=request.user)),
            count=Count('transactions', filter=Q(transactions__account__user=request.user))
        ).order_by('-total_amount')
    else:
        # Для неавторизованных пользователей - пустые queryset'ы
        expense_by_category = Category.objects.none()
        income_by_category = Category.objects.none()

    # Подготавливаем данные для диаграммы расходов (только категории с расходами)
    expense_chart_data = {
        'labels': [],
        'data': [],
        'colors': []
    }

    # Палитра с максимальным цветовым контрастом (различимы даже при дальтонизме)
    # Используем научно подобранные цвета из палитры Келли и качественных палитр ColorBrewer
    default_colors = [
        '#e6194b',  # Красный
        '#3cb44b',  # Зеленый
        '#ffe119',  # Желтый
        '#4363d8',  # Синий
        '#f58231',  # Оранжевый
        '#911eb4',  # Фиолетовый
        '#46f0f0',  # Циан
        '#f032e6',  # Маджента
        '#bcf60c',  # Лайм
        '#fabebe',  # Розовый
        '#008080',  # Морской волны
        '#e6beff',  # Лавандовый
        '#9a6324',  # Коричневый
        '#fffac8',  # Бежевый
        '#800000',  # Бордовый
        '#aaffc3',  # Мятный
        '#808000',  # Оливковый
        '#ffd8b1',  # Персиковый
        '#000075',  # Темно-синий
        '#808080',  # Серый
    ]

    for idx, category in enumerate(expense_by_category):
        if category.total_amount:  # Только если есть транзакции
            expense_chart_data['labels'].append(category.category_name)
            expense_chart_data['data'].append(float(category.total_amount))
            # Используем цвет категории или цвет по умолчанию
            expense_chart_data['colors'].append(
                category.color if category.color else default_colors[idx % len(default_colors)]
            )

    # Подготавливаем данные для столбчатой диаграммы сравнения доходов и расходов
    # По умолчанию показываем данные за 30 дней
    if request.user.is_authenticated:
        comparison_chart_data = calculate_comparison_data(request.user, 30)
    else:
        comparison_chart_data = {'labels': [], 'expenses': [], 'incomes': []}

    # Подготавливаем данные для линейного графика динамики баланса (по умолчанию 30 дней)
    if request.user.is_authenticated:
        balance_chart_data = calculate_balance_history(request.user, 30)
    else:
        balance_chart_data = {'labels': [], 'data': []}

    context = {
        'expense_by_category': expense_by_category,
        'income_by_category': income_by_category,
        'expense_chart_data': expense_chart_data,
        'expense_chart_data_json': {
            'labels': json.dumps(expense_chart_data['labels']),
            'data': json.dumps(expense_chart_data['data']),
            'colors': json.dumps(expense_chart_data['colors'])
        },
        'comparison_chart_data_json': {
            'labels': json.dumps(comparison_chart_data['labels']),
            'expenses': json.dumps(comparison_chart_data['expenses']),
            'incomes': json.dumps(comparison_chart_data['incomes'])
        },
        'balance_chart_data_json': {
            'labels': json.dumps(balance_chart_data['labels']),
            'data': json.dumps(balance_chart_data['data'])
        }
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


@login_required
def account_add(request):
    """
    Создание нового счета для текущего пользователя
    """
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()
            messages.success(request, f'Счет "{account.account_name}" успешно создан!')
            return redirect('finance:accounts')
    else:
        form = AccountForm()

    return render(request, 'finance/account_form.html', {'form': form, 'title': 'Добавить новый счет'})


@login_required
def account_edit(request, pk):
    """
    Редактирование существующего счета
    """
    account = get_object_or_404(Account, pk=pk, user=request.user)

    if request.method == 'POST':
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, f'Счет "{account.account_name}" успешно обновлен!')
            return redirect('finance:accounts')
    else:
        form = AccountForm(instance=account)

    return render(request, 'finance/account_form.html', {'form': form, 'title': 'Редактировать счет', 'account': account})


@login_required
def account_delete(request, pk):
    """
    Удаление счета пользователя
    """
    account = get_object_or_404(Account, pk=pk, user=request.user)

    if request.method == 'POST':
        account_name = account.account_name
        account.delete()
        messages.success(request, f'Счет "{account_name}" успешно удален!')
        return redirect('finance:accounts')

    return render(request, 'finance/account_confirm_delete.html', {'account': account})


# ==================== БЮДЖЕТЫ ====================

def budgets(request):
    """
    Страница списка всех бюджетов пользователя
    """
    if request.user.is_authenticated:
        user_budgets = Budget.objects.filter(user=request.user).order_by('-start_date')
    else:
        user_budgets = Budget.objects.none()

    context = {
        'budgets': user_budgets,
        'budgets_count': user_budgets.count()
    }

    return render(request, 'finance/budgets.html', context)


@login_required
def budget_add(request):
    """
    Создание нового бюджета для текущего пользователя
    """
    if request.method == 'POST':
        form = BudgetForm(request.POST, user=request.user)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.save()
            messages.success(request, f'Бюджет "{budget.budget_name}" успешно создан!')
            return redirect('finance:index')
    else:
        form = BudgetForm(user=request.user)

    return render(request, 'finance/budget_form.html', {'form': form, 'title': 'Добавить новый бюджет'})


@login_required
def budget_edit(request, pk):
    """
    Редактирование существующего бюджета
    """
    budget = get_object_or_404(Budget, pk=pk, user=request.user)

    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Бюджет "{budget.budget_name}" успешно обновлен!')
            return redirect('finance:index')
    else:
        form = BudgetForm(instance=budget, user=request.user)

    return render(request, 'finance/budget_form.html', {'form': form, 'title': 'Редактировать бюджет', 'budget': budget})


@login_required
def budget_delete(request, pk):
    """
    Удаление бюджета пользователя
    """
    budget = get_object_or_404(Budget, pk=pk, user=request.user)

    if request.method == 'POST':
        budget_name = budget.budget_name
        budget.delete()
        messages.success(request, f'Бюджет "{budget_name}" успешно удален!')
        return redirect('finance:index')

    return render(request, 'finance/budget_confirm_delete.html', {'budget': budget})


# ==================== ТРАНЗАКЦИИ ====================

@login_required
def transaction_add(request):
    """
    Создание новой транзакции для текущего пользователя
    """
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save()
            messages.success(request, f'Транзакция на сумму {transaction.amount} успешно создана!')
            return redirect('finance:transactions')
    else:
        form = TransactionForm(user=request.user)

    return render(request, 'finance/transaction_form.html', {'form': form, 'title': 'Добавить транзакцию'})


@login_required
def transaction_edit(request, pk):
    """
    Редактирование существующей транзакции
    """
    transaction = get_object_or_404(Transaction, pk=pk, account__user=request.user)

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Транзакция успешно обновлена!')
            return redirect('finance:transactions')
    else:
        form = TransactionForm(instance=transaction, user=request.user)

    return render(request, 'finance/transaction_form.html', {'form': form, 'title': 'Редактировать транзакцию', 'transaction': transaction})


@login_required
def transaction_delete(request, pk):
    """
    Удаление транзакции пользователя
    """
    transaction = get_object_or_404(Transaction, pk=pk, account__user=request.user)

    if request.method == 'POST':
        amount = transaction.amount
        transaction.delete()
        messages.success(request, f'Транзакция на сумму {amount} успешно удалена!')
        return redirect('finance:transactions')

    return render(request, 'finance/transaction_confirm_delete.html', {'transaction': transaction})


# ==================== ИНВЕСТИЦИИ (АКЦИИ) ====================

@login_required
def stock_add(request):
    """
    Добавление новой акции в портфель
    """
    if request.method == 'POST':
        form = StockForm(request.POST)
        if form.is_valid():
            stock = form.save(commit=False)
            stock.user = request.user

            # Пытаемся получить название компании, если оно не указано
            if not stock.company_name:
                stock_info = StockService.get_stock_price(stock.ticker)
                if stock_info:
                    stock.company_name = stock_info.get('name', stock.ticker)

            stock.save()
            messages.success(request, f'Акция {stock.ticker} успешно добавлена в портфель!')
            return redirect('finance:investments')
    else:
        form = StockForm()

    return render(request, 'finance/stock_form.html', {
        'form': form,
        'title': 'Добавить акцию в портфель'
    })


@login_required
def stock_edit(request, pk):
    """
    Редактирование акции в портфеле
    """
    stock = get_object_or_404(Stock, pk=pk, user=request.user)

    if request.method == 'POST':
        form = StockForm(request.POST, instance=stock)
        if form.is_valid():
            stock = form.save()
            messages.success(request, f'Акция {stock.ticker} успешно обновлена!')
            return redirect('finance:investments')
    else:
        form = StockForm(instance=stock)

    return render(request, 'finance/stock_form.html', {
        'form': form,
        'title': 'Редактировать акцию',
        'stock': stock
    })


@login_required
def stock_delete(request, pk):
    """
    Удаление акции из портфеля
    """
    stock = get_object_or_404(Stock, pk=pk, user=request.user)

    if request.method == 'POST':
        ticker = stock.ticker
        stock.delete()
        messages.success(request, f'Акция {ticker} успешно удалена из портфеля!')
        return redirect('finance:investments')

    return render(request, 'finance/stock_confirm_delete.html', {'stock': stock})


@login_required
def get_stock_data(request):
    """
    AJAX endpoint для получения данных об акции
    Используется для автозаполнения названия компании
    """
    ticker = request.GET.get('ticker', '').upper()

    if not ticker:
        return JsonResponse({
            'success': False,
            'error': 'Тикер не указан'
        }, status=400)

    try:
        stock_data = StockService.get_stock_price(ticker)

        if stock_data:
            return JsonResponse({
                'success': True,
                'data': stock_data
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Не удалось найти данные для тикера {ticker}'
            }, status=404)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def get_balance_history(request):
    """
    AJAX endpoint для получения истории баланса за указанный период
    Параметры:
    - days: количество дней (30, 90, 365)
    """
    try:
        days = int(request.GET.get('days', 30))

        # Ограничиваем допустимые значения
        if days not in [30, 90, 365]:
            days = 30

        balance_data = calculate_balance_history(request.user, days)

        return JsonResponse({
            'success': True,
            'data': balance_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def get_comparison_data(request):
    """
    AJAX endpoint для получения данных сравнения доходов и расходов за указанный период
    Параметры:
    - days: количество дней (30, 90, 365) или 'all' для всего времени
    """
    try:
        days_param = request.GET.get('days', '30')

        # Определяем период
        if days_param == 'all':
            days = None  # Все время
        else:
            days = int(days_param)
            # Ограничиваем допустимые значения
            if days not in [30, 90, 365]:
                days = 30

        comparison_data = calculate_comparison_data(request.user, days)

        return JsonResponse({
            'success': True,
            'data': comparison_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
