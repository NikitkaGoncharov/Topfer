from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum
from import_export.admin import ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from .models import User, Currency, Category, Account, Tag, Transaction, TransactionTag, Budget, Stock
from .resources import AccountResource, TransactionResource, BudgetResource


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name', 'subscription_type', 'is_active', 'registration_date', 'accounts_count', 'transactions_count']
    list_filter = ['subscription_type', 'is_active', 'registration_date']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['registration_date', 'last_login', 'accounts_count', 'transactions_count', 'total_balance']
    date_hierarchy = 'registration_date'
    list_display_links = ['email', 'full_name']

    fieldsets = (
        ('Основная информация', {
            'fields': ('email', 'password_hash', 'first_name', 'last_name')
        }),
        ('Подписка и статус', {
            'fields': ('subscription_type', 'is_active')
        }),
        ('Даты', {
            'fields': ('registration_date', 'last_login')
        }),
        ('Статистика', {
            'fields': ('accounts_count', 'transactions_count', 'total_balance'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Полное имя')
    def full_name(self, obj):
        """Возвращает полное имя пользователя"""
        if obj.first_name or obj.last_name:
            return f"{obj.first_name} {obj.last_name}".strip()
        return '—'

    @admin.display(description='Кол-во счетов')
    def accounts_count(self, obj):
        """Возвращает количество счетов пользователя"""
        return obj.accounts.count()

    @admin.display(description='Кол-во транзакций')
    def transactions_count(self, obj):
        """Возвращает общее количество транзакций по всем счетам пользователя"""
        return sum(account.transactions.count() for account in obj.accounts.all())

    @admin.display(description='Общий баланс')
    def total_balance(self, obj):
        """Возвращает общий баланс пользователя по всем валютам"""
        accounts = obj.accounts.select_related('currency').all()
        if not accounts:
            return '—'
        balances = {}
        for account in accounts:
            currency = account.currency.currency_code
            if currency not in balances:
                balances[currency] = 0
            balances[currency] += account.balance
        return ', '.join([f"{amount} {curr}" for curr, amount in balances.items()])


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['currency_code', 'currency_name', 'symbol', 'accounts_count']
    search_fields = ['currency_code', 'currency_name']
    list_display_links = ['currency_code', 'currency_name']
    readonly_fields = ['accounts_count']

    @admin.display(description='Кол-во счетов')
    def accounts_count(self, obj):
        """Возвращает количество счетов использующих данную валюту"""
        return obj.accounts.count()


class SubcategoryInline(admin.TabularInline):
    model = Category
    fk_name = 'parent_category'
    extra = 0
    fields = ['category_name', 'category_type', 'icon', 'color', 'is_system']
    verbose_name = 'Подкатегория'
    verbose_name_plural = 'Подкатегории'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['category_name', 'category_type', 'parent_category', 'color_preview', 'is_system', 'transactions_count', 'budgets_count']
    list_filter = ['category_type', 'is_system', 'parent_category']
    search_fields = ['category_name']
    list_display_links = ['category_name']
    inlines = [SubcategoryInline]
    readonly_fields = ['transactions_count', 'budgets_count']

    fieldsets = (
        ('Основная информация', {
            'fields': ('category_name', 'category_type', 'parent_category')
        }),
        ('Оформление', {
            'fields': ('icon', 'color', 'is_system')
        }),
        ('Статистика', {
            'fields': ('transactions_count', 'budgets_count'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Цвет')
    def color_preview(self, obj):
        """Отображает превью цвета категории в виде квадрата"""
        if obj.color:
            return format_html(
                '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
                obj.color
            )
        return '—'

    @admin.display(description='Кол-во транзакций')
    def transactions_count(self, obj):
        """Возвращает количество транзакций в данной категории"""
        return obj.transactions.count()

    @admin.display(description='Кол-во бюджетов')
    def budgets_count(self, obj):
        """Возвращает количество бюджетов привязанных к данной категории"""
        return obj.budgets.count()


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    fields = ['transaction_date', 'transaction_type', 'category', 'amount', 'description']
    readonly_fields = ['transaction_date']
    raw_id_fields = ['category']
    verbose_name = 'Транзакция'
    verbose_name_plural = 'Транзакции'
    show_change_link = True


@admin.register(Account)
class AccountAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = AccountResource  # Подключаем Resource для экспорта
    list_display = ['account_name', 'user_email', 'account_type', 'balance_display', 'currency', 'bank_connected', 'created_date', 'transactions_count']
    list_filter = ['account_type', 'currency', 'bank_connected', 'created_date']
    search_fields = ['account_name', 'user__email', 'user__first_name', 'user__last_name']
    raw_id_fields = ['user']
    list_display_links = ['account_name']
    readonly_fields = ['created_date', 'transactions_count', 'total_income', 'total_expense']
    date_hierarchy = 'created_date'
    inlines = [TransactionInline]
    history_list_display = ['balance']  # Показываем историю изменений баланса

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'account_name', 'account_type', 'currency')
        }),
        ('Баланс', {
            'fields': ('balance', 'bank_connected')
        }),
        ('Даты', {
            'fields': ('created_date',)
        }),
        ('Статистика', {
            'fields': ('transactions_count', 'total_income', 'total_expense'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Email пользователя', ordering='user__email')
    def user_email(self, obj):
        """Возвращает email пользователя владельца счета"""
        return obj.user.email

    @admin.display(description='Баланс')
    def balance_display(self, obj):
        """Отображает баланс счета с символом валюты"""
        return format_html(
            '<strong>{} {}</strong>',
            obj.balance,
            obj.currency.symbol or obj.currency.currency_code
        )

    @admin.display(description='Кол-во транзакций')
    def transactions_count(self, obj):
        """Возвращает количество транзакций по данному счету"""
        return obj.transactions.count()

    @admin.display(description='Всего доходов')
    def total_income(self, obj):
        """Возвращает сумму всех доходов по данному счету"""
        total = obj.transactions.filter(transaction_type='income').aggregate(Sum('amount'))['amount__sum'] or 0
        return f"{total} {obj.currency.currency_code}"

    @admin.display(description='Всего расходов')
    def total_expense(self, obj):
        """Возвращает сумму всех расходов по данному счету"""
        total = obj.transactions.filter(transaction_type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
        return f"{total} {obj.currency.currency_code}"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['tag_name', 'user_email', 'color_preview', 'transactions_count']
    list_filter = ['user']
    search_fields = ['tag_name', 'user__email']
    raw_id_fields = ['user']
    list_display_links = ['tag_name']
    readonly_fields = ['transactions_count']

    @admin.display(description='Email пользователя', ordering='user__email')
    def user_email(self, obj):
        """Возвращает email пользователя владельца тега"""
        return obj.user.email

    @admin.display(description='Цвет')
    def color_preview(self, obj):
        """Отображает превью цвета тега в виде квадрата"""
        if obj.color:
            return format_html(
                '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
                obj.color
            )
        return '—'

    @admin.display(description='Кол-во транзакций')
    def transactions_count(self, obj):
        """Возвращает количество транзакций отмеченных данным тегом"""
        return obj.transactions.count()


@admin.register(TransactionTag)
class TransactionTagAdmin(admin.ModelAdmin):
    """Админка для промежуточной модели TransactionTag"""
    list_display = ['transaction', 'tag', 'added_date', 'added_by']
    list_filter = ['added_date', 'tag']
    search_fields = ['transaction__description', 'tag__tag_name']
    raw_id_fields = ['transaction', 'tag', 'added_by']
    readonly_fields = ['added_date']


class TransactionTagInline(admin.TabularInline):
    """Inline для управления тегами транзакций через промежуточную модель"""
    model = TransactionTag
    extra = 1
    raw_id_fields = ['tag', 'added_by']
    readonly_fields = ['added_date']


@admin.register(Transaction)
class TransactionAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = TransactionResource  # Подключаем Resource для экспорта
    list_display = ['transaction_id', 'account_name', 'transaction_type', 'amount_display', 'category', 'transaction_date', 'is_recurring', 'tags_list']
    list_filter = ['transaction_type', 'is_recurring', 'transaction_date', 'account__account_type', 'category__category_type']
    search_fields = ['description', 'account__account_name', 'account__user__email', 'category__category_name']
    raw_id_fields = ['account', 'category']
    list_display_links = ['transaction_id', 'account_name']
    readonly_fields = ['transaction_date', 'receipt_preview']
    date_hierarchy = 'transaction_date'
    history_list_display = ['amount', 'transaction_type']  # История изменений суммы и типа
    filter_horizontal = ['tags']  # Удобный виджет для выбора тегов
    inlines = [TransactionTagInline]  # Добавляем inline для тегов (для демонстрации)

    fieldsets = (
        ('Основная информация', {
            'fields': ('account', 'transaction_type', 'amount', 'category')
        }),
        ('Детали', {
            'fields': ('transaction_date', 'description', 'is_recurring')
        }),
        ('Теги', {
            'fields': ('tags',)
        }),
        ('Чек', {
            'fields': ('receipt_photo', 'receipt_preview'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='ID', ordering='id')
    def transaction_id(self, obj):
        """Возвращает ID транзакции в формате #ID"""
        return f"#{obj.id}"

    @admin.display(description='Счет', ordering='account__account_name')
    def account_name(self, obj):
        """Возвращает название счета транзакции"""
        return obj.account.account_name

    @admin.display(description='Сумма')
    def amount_display(self, obj):
        """Отображает сумму транзакции с цветовым кодированием по типу"""
        color = 'green' if obj.transaction_type == 'income' else 'red' if obj.transaction_type == 'expense' else 'blue'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            obj.amount,
            obj.account.currency.symbol or obj.account.currency.currency_code
        )

    @admin.display(description='Теги')
    def tags_list(self, obj):
        """Возвращает список тегов транзакции (максимум 3 + счетчик остальных)"""
        tags = obj.tags.all()[:3]
        if not tags:
            return '—'
        result = ', '.join([tag.tag_name for tag in tags])
        if obj.tags.count() > 3:
            result += f' (+{obj.tags.count() - 3})'
        return result

    @admin.display(description='Превью чека')
    def receipt_preview(self, obj):
        """Отображает превью фотографии чека если она есть"""
        if obj.receipt_photo:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px;" />',
                obj.receipt_photo.url
            )
        return 'Нет чека'


@admin.register(Budget)
class BudgetAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = BudgetResource  # Подключаем Resource для экспорта
    list_display = ['budget_name', 'user_email', 'amount_display', 'period_type', 'start_date', 'end_date', 'category', 'is_active']
    list_filter = ['period_type', 'start_date', 'user']
    search_fields = ['budget_name', 'user__email', 'category__category_name']
    raw_id_fields = ['user', 'category']
    list_display_links = ['budget_name']
    date_hierarchy = 'start_date'
    history_list_display = ['amount', 'start_date', 'end_date']  # История изменений суммы и дат

    def get_readonly_fields(self, request, obj=None):
        """Возвращает список полей только для чтения при редактировании бюджета"""
        # Показываем readonly поля только при редактировании (когда obj существует)
        if obj:
            return ['is_active', 'days_left']
        return []

    def get_fieldsets(self, request, obj=None):
        """Возвращает структуру полей формы в зависимости от режима (создание/редактирование)"""
        # Показываем секцию "Статус" только при редактировании
        if obj:
            return (
                ('Основная информация', {
                    'fields': ('user', 'budget_name', 'amount', 'category')
                }),
                ('Период', {
                    'fields': ('period_type', 'start_date', 'end_date')
                }),
                ('Статус', {
                    'fields': ('is_active', 'days_left'),
                    'classes': ('collapse',)
                }),
            )
        else:
            return (
                ('Основная информация', {
                    'fields': ('user', 'budget_name', 'amount', 'category')
                }),
                ('Период', {
                    'fields': ('period_type', 'start_date', 'end_date')
                }),
            )

    @admin.display(description='Email пользователя', ordering='user__email')
    def user_email(self, obj):
        """Возвращает email пользователя владельца бюджета"""
        return obj.user.email

    @admin.display(description='Сумма')
    def amount_display(self, obj):
        """Отображает сумму бюджета с валютой пользователя"""
        # Получаем валюту из первого счета пользователя или показываем просто сумму
        account = obj.user.accounts.first()
        currency = account.currency.currency_code if account else ''
        return format_html(
            '<strong>{} {}</strong>',
            obj.amount,
            currency
        )

    @admin.display(description='Активен', boolean=True)
    def is_active(self, obj):
        """Проверяет активен ли бюджет на текущую дату"""
        from django.utils import timezone
        # Если бюджет еще не сохранен (создается), start_date может быть None
        if not obj.start_date:
            return None
        today = timezone.now().date()
        if obj.end_date:
            return obj.start_date <= today <= obj.end_date
        return obj.start_date <= today

    @admin.display(description='Дней осталось')
    def days_left(self, obj):
        """Возвращает количество дней до окончания бюджета"""
        from django.utils import timezone
        # Если бюджет еще не сохранен, start_date может быть None
        if not obj.start_date:
            return '—'
        if not obj.end_date:
            return 'Бессрочный'
        today = timezone.now().date()
        if obj.end_date < today:
            return 'Завершен'
        days = (obj.end_date - today).days
        return f"{days} дн."


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    """Админка для управления акциями в портфеле"""
    list_display = ['ticker', 'company_name', 'user_email', 'quantity', 'purchase_price_display', 'purchase_date', 'total_investment_display']
    list_filter = ['purchase_date', 'currency', 'user']
    search_fields = ['ticker', 'company_name', 'user__email', 'user__username']
    raw_id_fields = ['user']
    list_display_links = ['ticker', 'company_name']
    readonly_fields = ['created_date', 'total_investment_display']
    date_hierarchy = 'purchase_date'

    fieldsets = (
        ('Информация об акции', {
            'fields': ('ticker', 'company_name')
        }),
        ('Покупка', {
            'fields': ('user', 'quantity', 'purchase_price', 'purchase_date', 'currency')
        }),
        ('Дополнительно', {
            'fields': ('notes', 'created_date', 'total_investment_display')
        }),
    )

    @admin.display(description='Email пользователя', ordering='user__email')
    def user_email(self, obj):
        """Возвращает email пользователя владельца акции"""
        return obj.user.email

    @admin.display(description='Цена покупки')
    def purchase_price_display(self, obj):
        """Отображает цену покупки с валютой"""
        return format_html(
            '<strong>{} {}</strong>',
            obj.purchase_price,
            obj.currency.symbol or obj.currency.currency_code
        )

    @admin.display(description='Сумма инвестиции')
    def total_investment_display(self, obj):
        """Отображает общую сумму инвестиции"""
        total = obj.total_investment
        return format_html(
            '<strong style="color: #0066cc;">{} {}</strong>',
            total,
            obj.currency.symbol or obj.currency.currency_code
        )
