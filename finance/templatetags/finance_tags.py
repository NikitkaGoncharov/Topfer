from django import template
from django.utils import timezone
from django.db.models import Sum
from finance.models import Transaction, Budget, Account

register = template.Library()


# 1. Простой шаблонный тег
@register.simple_tag
def current_time(format_string='%d.%m.%Y %H:%M'):
    """
    Простой тег, возвращающий текущее время в заданном формате
    Использование: {% current_time "%d.%m.%Y" %}
    """
    return timezone.now().strftime(format_string)


@register.simple_tag
def multiply(a, b):
    """
    Простой тег для умножения двух чисел
    Использование: {% multiply 5 10 %}
    """
    return float(a) * float(b)


# 2. Шаблонный тег с контекстными переменными
@register.simple_tag(takes_context=True)
def user_balance(context):
    """
    Тег с контекстом, возвращающий общий баланс пользователя
    Использование: {% user_balance %}
    """
    user = context.get('user')
    if user and user.is_authenticated:
        total = Account.objects.filter(user=user).aggregate(
            total=Sum('balance')
        )['total'] or 0
        return f"{total:.2f}"
    return "0.00"


@register.simple_tag(takes_context=True)
def user_transactions_count(context, transaction_type=None):
    """
    Тег с контекстом, возвращающий количество транзакций пользователя
    Использование: {% user_transactions_count "income" %}
    """
    user = context.get('user')
    if user and user.is_authenticated:
        queryset = Transaction.objects.filter(account__user=user)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        return queryset.count()
    return 0


# 3. Шаблонный тег, возвращающий набор запросов (inclusion tag)
@register.inclusion_tag('finance/widgets/recent_transactions.html', takes_context=True)
def show_recent_transactions(context, limit=5):
    """
    Inclusion tag, возвращающий набор последних транзакций
    Использование: {% show_recent_transactions 10 %}
    """
    user = context.get('user')
    transactions = []

    if user and user.is_authenticated:
        transactions = Transaction.objects.filter(
            account__user=user
        ).select_related(
            'account', 'category', 'account__currency'
        ).order_by('-transaction_date')[:limit]

    return {
        'transactions': transactions,
        'user': user
    }


@register.inclusion_tag('finance/widgets/active_budgets.html', takes_context=True)
def show_active_budgets(context, limit=5):
    """
    Inclusion tag, возвращающий активные бюджеты пользователя
    Использование: {% show_active_budgets 3 %}
    """
    user = context.get('user')
    budgets = []

    if user and user.is_authenticated:
        from django.db.models import Q
        today = timezone.now().date()
        budgets = Budget.objects.filter(
            user=user
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today),
            start_date__lte=today
        ).select_related('category')[:limit]

    return {
        'budgets': budgets,
        'user': user
    }


# Дополнительные фильтры
@register.filter
def currency_symbol(value):
    """
    Фильтр для добавления символа валюты
    Использование: {{ amount|currency_symbol }}
    """
    return f"{value} ₽"


@register.filter
def transaction_icon(transaction_type):
    """
    Фильтр для возврата иконки по типу транзакции
    Использование: {{ transaction.transaction_type|transaction_icon }}
    """
    icons = {
        'income': '📈',
        'expense': '📉',
        'transfer': '🔄'
    }
    return icons.get(transaction_type, '💰')
