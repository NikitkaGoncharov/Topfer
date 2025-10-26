from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.db.models import Sum, Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta

from .models import User, Currency, Category, Account, Tag, Transaction, Budget, Stock
from .serializers import (
    UserSerializer, CurrencySerializer, CategorySerializer,
    AccountSerializer, TagSerializer, TransactionSerializer,
    BudgetSerializer, StockSerializer
)


class CurrencyViewSet(viewsets.ModelViewSet):
    """ViewSet для валют"""

    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['currency_code', 'currency_name']
    ordering_fields = ['currency_code', 'currency_name']


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet для категорий"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['category_name']
    ordering_fields = ['category_name', 'category_type']
    filterset_fields = ['category_type', 'is_system', 'parent_category']

    @action(detail=False, methods=['get'])
    def income(self, request):
        """Получить только категории доходов"""
        income_categories = self.queryset.filter(category_type='income')
        serializer = self.get_serializer(income_categories, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def expense(self, request):
        """Получить только категории расходов"""
        expense_categories = self.queryset.filter(category_type='expense')
        serializer = self.get_serializer(expense_categories, many=True)
        return Response(serializer.data)


class TagViewSet(viewsets.ModelViewSet):
    """ViewSet для тегов"""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['tag_name']
    ordering_fields = ['tag_name']

    def get_queryset(self):
        """Только теги текущего пользователя"""
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Привязываем тег к текущему пользователю"""
        serializer.save(user=self.request.user)


class AccountViewSet(viewsets.ModelViewSet):
    """ViewSet для счетов"""

    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['account_name']
    ordering_fields = ['balance', 'created_date', 'account_name']
    filterset_fields = ['account_type', 'currency', 'bank_connected']

    def get_queryset(self):
        """Только счета текущего пользователя"""
        return self.queryset.filter(user=self.request.user).select_related('currency')

    def perform_create(self, serializer):
        """Привязываем счет к текущему пользователю"""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def total_balance(self, request):
        """Общий баланс по всем счетам пользователя"""
        user_accounts = self.get_queryset()

        total = user_accounts.aggregate(total=Sum('balance'))['total'] or 0

        # Баланс по валютам
        by_currency = {}
        for account in user_accounts:
            currency = account.currency.currency_code
            if currency not in by_currency:
                by_currency[currency] = 0
            by_currency[currency] += float(account.balance)

        return Response({
            'total_balance': float(total),
            'accounts_count': user_accounts.count(),
            'by_currency': by_currency
        })


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet для транзакций"""

    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['description', 'account__account_name', 'category__category_name']
    ordering_fields = ['transaction_date', 'amount']
    filterset_fields = ['transaction_type', 'category', 'account', 'is_recurring']

    def get_queryset(self):
        """Только транзакции текущего пользователя"""
        return self.queryset.filter(
            account__user=self.request.user
        ).select_related(
            'account', 'category', 'account__currency'
        ).prefetch_related('tags')

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Последние 10 транзакций"""
        recent_transactions = self.get_queryset().order_by('-transaction_date')[:10]
        serializer = self.get_serializer(recent_transactions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Статистика по транзакциям за период"""
        days = int(request.query_params.get('days', 30))
        start_date = datetime.now() - timedelta(days=days)

        transactions = self.get_queryset().filter(transaction_date__gte=start_date)

        income = transactions.filter(transaction_type='income').aggregate(
            total=Sum('amount')
        )['total'] or 0

        expense = transactions.filter(transaction_type='expense').aggregate(
            total=Sum('amount')
        )['total'] or 0

        return Response({
            'period_days': days,
            'total_income': float(income),
            'total_expense': float(expense),
            'net_income': float(income - expense),
            'transactions_count': transactions.count()
        })

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Дублировать транзакцию"""
        transaction = self.get_object()

        new_transaction = Transaction.objects.create(
            account=transaction.account,
            category=transaction.category,
            amount=transaction.amount,
            transaction_type=transaction.transaction_type,
            description=f"[Копия] {transaction.description}",
            is_recurring=transaction.is_recurring
        )

        new_transaction.tags.set(transaction.tags.all())

        serializer = self.get_serializer(new_transaction)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BudgetViewSet(viewsets.ModelViewSet):
    """ViewSet для бюджетов"""

    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['budget_name']
    ordering_fields = ['start_date', 'amount']
    filterset_fields = ['period_type', 'category']

    def get_queryset(self):
        """Только бюджеты текущего пользователя"""
        return self.queryset.filter(user=self.request.user).select_related('category')

    def perform_create(self, serializer):
        """Привязываем бюджет к текущему пользователю"""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Активные бюджеты на текущую дату"""
        from django.utils import timezone
        today = timezone.now().date()

        active_budgets = self.get_queryset().filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today),
            start_date__lte=today
        )

        serializer = self.get_serializer(active_budgets, many=True)
        return Response(serializer.data)


class StockViewSet(viewsets.ModelViewSet):
    """ViewSet для акций"""

    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['ticker', 'company_name']
    ordering_fields = ['purchase_date', 'purchase_price']
    filterset_fields = ['currency']

    def get_queryset(self):
        """Только акции текущего пользователя"""
        return self.queryset.filter(user=self.request.user).select_related('currency')

    def perform_create(self, serializer):
        """Привязываем акцию к текущему пользователю"""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def portfolio_summary(self, request):
        """Сводка по инвестиционному портфелю"""
        user_stocks = self.get_queryset()

        total_investment = sum(float(stock.total_investment) for stock in user_stocks)

        # Группировка по валютам
        by_currency = {}
        for stock in user_stocks:
            currency = stock.currency.currency_code
            if currency not in by_currency:
                by_currency[currency] = 0
            by_currency[currency] += float(stock.total_investment)

        return Response({
            'total_investment': total_investment,
            'stocks_count': user_stocks.count(),
            'by_currency': by_currency
        })


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для пользователей (только чтение)"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['registration_date']

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Информация о текущем пользователе"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
