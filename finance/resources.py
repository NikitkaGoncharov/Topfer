from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, DateWidget
from .models import Account, Transaction, Budget


class AccountResource(resources.ModelResource):
    """
    Resource для экспорта счетов в Excel
    Кастомизация: 3 метода
    """
    currency_name = fields.Field(
        column_name='Валюта',
        attribute='currency',
        widget=ForeignKeyWidget(model='finance.Currency', field='currency_name')
    )

    class Meta:
        model = Account
        fields = ('id', 'user__email', 'account_name', 'account_type', 'currency_name', 'balance', 'bank_connected', 'created_date')
        export_order = fields

    def get_export_queryset(self, queryset):
        """
        Метод 1: Кастомизация queryset для экспорта
        Экспортируем только счета с балансом больше 0
        """
        return queryset.filter(balance__gt=0).select_related('currency', 'user')

    def dehydrate_account_name(self, account):
        """
        Метод 2: Кастомизация поля account_name
        Добавляем префикс к названию счета
        """
        return f"[{account.get_account_type_display()}] {account.account_name}"

    def dehydrate_balance(self, account):
        """
        Метод 3: Кастомизация поля balance
        Форматируем баланс с символом валюты
        """
        return f"{account.balance} {account.currency.symbol or account.currency.currency_code}"


class TransactionResource(resources.ModelResource):
    """
    Resource для экспорта транзакций в Excel
    Кастомизация: 3 метода
    """
    account_name = fields.Field(
        column_name='Счет',
        attribute='account__account_name'
    )
    category_name = fields.Field(
        column_name='Категория',
        attribute='category__category_name'
    )

    class Meta:
        model = Transaction
        fields = ('id', 'account_name', 'category_name', 'amount', 'transaction_type', 'transaction_date', 'description', 'is_recurring')
        export_order = fields

    def get_export_queryset(self, queryset):
        """
        Метод 1: Экспортируем только транзакции за последние 90 дней
        """
        from datetime import datetime, timedelta
        ninety_days_ago = datetime.now() - timedelta(days=90)
        return queryset.filter(
            transaction_date__gte=ninety_days_ago
        ).select_related('account', 'category')

    def dehydrate_transaction_date(self, transaction):
        """
        Метод 2: Форматируем дату в читаемый формат
        """
        return transaction.transaction_date.strftime('%d.%m.%Y %H:%M')

    def dehydrate_amount(self, transaction):
        """
        Метод 3: Добавляем знак + или - к сумме в зависимости от типа транзакции
        """
        if transaction.transaction_type == 'income':
            return f"+{transaction.amount}"
        elif transaction.transaction_type == 'expense':
            return f"-{transaction.amount}"
        return str(transaction.amount)


class BudgetResource(resources.ModelResource):
    """
    Resource для экспорта бюджетов в Excel
    Кастомизация: 3 метода
    """
    category_name = fields.Field(
        column_name='Категория',
        attribute='category__category_name'
    )

    class Meta:
        model = Budget
        fields = ('id', 'user__email', 'budget_name', 'amount', 'period_type', 'start_date', 'end_date', 'category_name')
        export_order = fields

    def get_export_queryset(self, queryset):
        """
        Метод 1: Экспортируем только активные бюджеты
        """
        from django.utils import timezone
        from django.db.models import Q
        today = timezone.now().date()
        return queryset.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today),
            start_date__lte=today
        ).select_related('category', 'user')

    def dehydrate_budget_name(self, budget):
        """
        Метод 2: Добавляем тип периода к названию бюджета
        """
        return f"{budget.budget_name} ({budget.get_period_type_display()})"

    def dehydrate_start_date(self, budget):
        """
        Метод 3: Форматируем дату начала в формат ДД.ММ.ГГГГ
        """
        return budget.start_date.strftime('%d.%m.%Y')
