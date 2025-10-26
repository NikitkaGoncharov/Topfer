from rest_framework import serializers
from .models import User, Currency, Category, Account, Tag, Transaction, Budget, Stock


class CurrencySerializer(serializers.ModelSerializer):
    """Сериализатор для валют"""

    class Meta:
        model = Currency
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор для категорий"""

    parent_category_name = serializers.SerializerMethodField()
    category_type_display = serializers.CharField(source='get_category_type_display', read_only=True)

    class Meta:
        model = Category
        fields = '__all__'

    def get_parent_category_name(self, obj):
        if obj.parent_category:
            return obj.parent_category.category_name
        return None


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов"""

    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Tag
        fields = ['id', 'user', 'tag_name', 'color', 'user_email']


class AccountSerializer(serializers.ModelSerializer):
    """Сериализатор для счетов"""

    currency_detail = CurrencySerializer(source='currency', read_only=True)
    currency = serializers.PrimaryKeyRelatedField(queryset=Currency.objects.all(), write_only=True)
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Account
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    """Сериализатор для транзакций"""

    # Вложенные данные для чтения
    account_detail = AccountSerializer(source='account', read_only=True)
    category_detail = CategorySerializer(source='category', read_only=True)
    tags_detail = TagSerializer(source='tags', many=True, read_only=True)

    # ID для записи
    account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False, allow_null=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)

    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)

    class Meta:
        model = Transaction
        fields = '__all__'

    def validate_amount(self, value):
        """Сумма должна быть больше нуля"""
        if value <= 0:
            raise serializers.ValidationError("Сумма транзакции должна быть больше нуля")
        return value

    def validate(self, data):
        """Проверка соответствия категории типу транзакции"""
        if data.get('category') and data.get('transaction_type'):
            category = data['category']
            transaction_type = data['transaction_type']

            if transaction_type == 'income' and category.category_type != 'income':
                raise serializers.ValidationError({
                    'category': 'Для транзакции типа "доход" нужна категория типа "доход"'
                })

            if transaction_type == 'expense' and category.category_type != 'expense':
                raise serializers.ValidationError({
                    'category': 'Для транзакции типа "расход" нужна категория типа "расход"'
                })

        return data


class BudgetSerializer(serializers.ModelSerializer):
    """Сериализатор для бюджетов"""

    category_detail = CategorySerializer(source='category', read_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False, allow_null=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    period_type_display = serializers.CharField(source='get_period_type_display', read_only=True)

    class Meta:
        model = Budget
        fields = '__all__'

    def validate(self, data):
        """Дата окончания не может быть раньше даты начала"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': 'Дата окончания не может быть раньше даты начала'
            })

        return data


class StockSerializer(serializers.ModelSerializer):
    """Сериализатор для акций"""

    currency_detail = CurrencySerializer(source='currency', read_only=True)
    currency = serializers.PrimaryKeyRelatedField(queryset=Currency.objects.all())
    user_email = serializers.EmailField(source='user.email', read_only=True)
    total_investment = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = '__all__'

    def get_total_investment(self, obj):
        """Общая сумма инвестиции"""
        return float(obj.total_investment)

    def validate_quantity(self, value):
        """Количество акций должно быть больше нуля"""
        if value <= 0:
            raise serializers.ValidationError("Количество акций должно быть больше нуля")
        return value

    def validate_purchase_price(self, value):
        """Цена покупки должна быть больше нуля"""
        if value <= 0:
            raise serializers.ValidationError("Цена покупки должна быть больше нуля")
        return value


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователей (без пароля)"""

    subscription_type_display = serializers.CharField(source='get_subscription_type_display', read_only=True)
    accounts_count = serializers.SerializerMethodField()
    total_balance = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'subscription_type', 'subscription_type_display',
            'registration_date', 'last_login', 'is_active',
            'accounts_count', 'total_balance'
        ]

    def get_accounts_count(self, obj):
        """Количество счетов пользователя"""
        return obj.accounts.count()

    def get_total_balance(self, obj):
        """Общий баланс по всем счетам"""
        from django.db.models import Sum
        total = obj.accounts.aggregate(total=Sum('balance'))['total']
        return float(total) if total else 0.0
