from django.db import models
from django.core.validators import EmailValidator
from django.utils import timezone


class User(models.Model):
    """Модель пользователя системы"""
    email = models.EmailField(
        max_length=255,
        unique=True,
        validators=[EmailValidator()],
        verbose_name='Email'
    )
    password_hash = models.CharField(
        max_length=255,
        verbose_name='Хеш пароля'
    )
    first_name = models.CharField(
        max_length=100,
        verbose_name='Имя',
        blank=True
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name='Фамилия',
        blank=True
    )
    subscription_type = models.CharField(
        max_length=50,
        choices=[
            ('free', 'Бесплатная'),
            ('premium', 'Премиум'),
            ('business', 'Бизнес'),
        ],
        default='free',
        verbose_name='Тип подписки'
    )
    registration_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата регистрации'
    )
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Последний вход'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-registration_date']

    def __str__(self):
        """Возвращает строковое представление пользователя"""
        return f"{self.email} ({self.get_subscription_type_display()})"


class Currency(models.Model):
    """Модель валюты"""
    currency_code = models.CharField(
        max_length=3,
        unique=True,
        verbose_name='Код валюты'
    )
    currency_name = models.CharField(
        max_length=100,
        verbose_name='Название валюты'
    )
    symbol = models.CharField(
        max_length=10,
        verbose_name='Символ',
        blank=True
    )

    class Meta:
        verbose_name = 'Валюта'
        verbose_name_plural = 'Валюты'
        ordering = ['currency_code']

    def __str__(self):
        """Возвращает строковое представление валюты"""
        return f"{self.currency_code} - {self.currency_name}"


class Category(models.Model):
    """Модель категории транзакций"""
    category_name = models.CharField(
        max_length=100,
        verbose_name='Название категории'
    )
    category_type = models.CharField(
        max_length=20,
        choices=[
            ('income', 'Доход'),
            ('expense', 'Расход'),
        ],
        verbose_name='Тип категории'
    )
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategories',
        verbose_name='Родительская категория'
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Иконка'
    )
    color = models.CharField(
        max_length=7,
        blank=True,
        verbose_name='Цвет'
    )
    is_system = models.BooleanField(
        default=False,
        verbose_name='Системная категория'
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['category_type', 'category_name']

    def __str__(self):
        """Возвращает строковое представление категории с учетом родительской категории"""
        if self.parent_category:
            return f"{self.parent_category.category_name} → {self.category_name}"
        return self.category_name


class Account(models.Model):
    """Модель счета пользователя"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='accounts',
        verbose_name='Пользователь'
    )
    account_name = models.CharField(
        max_length=100,
        verbose_name='Название счета'
    )
    account_type = models.CharField(
        max_length=50,
        choices=[
            ('cash', 'Наличные'),
            ('card', 'Карта'),
            ('bank', 'Банковский счет'),
            ('savings', 'Сберегательный счет'),
            ('investment', 'Инвестиционный счет'),
        ],
        verbose_name='Тип счета'
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='accounts',
        verbose_name='Валюта'
    )
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Баланс'
    )
    bank_connected = models.BooleanField(
        default=False,
        verbose_name='Подключен к банку'
    )
    created_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Счет'
        verbose_name_plural = 'Счета'
        ordering = ['-created_date']

    def __str__(self):
        """Возвращает строковое представление счета с балансом"""
        return f"{self.account_name} ({self.balance} {self.currency.currency_code})"


class Tag(models.Model):
    """Модель тега для транзакций"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tags',
        verbose_name='Пользователь'
    )
    tag_name = models.CharField(
        max_length=50,
        verbose_name='Название тега'
    )
    color = models.CharField(
        max_length=7,
        blank=True,
        verbose_name='Цвет'
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['tag_name']
        unique_together = ['user', 'tag_name']

    def __str__(self):
        """Возвращает строковое представление тега"""
        return self.tag_name


class Transaction(models.Model):
    """Модель транзакции"""
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Счет'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transactions',
        verbose_name='Категория'
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Сумма'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ('income', 'Доход'),
            ('expense', 'Расход'),
            ('transfer', 'Перевод'),
        ],
        verbose_name='Тип транзакции'
    )
    transaction_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата транзакции'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    receipt_photo = models.ImageField(
        upload_to='receipts/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Фото чека'
    )
    is_recurring = models.BooleanField(
        default=False,
        verbose_name='Повторяющаяся'
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='transactions',
        verbose_name='Теги'
    )

    class Meta:
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'
        ordering = ['-transaction_date']

    def __str__(self):
        """Возвращает строковое представление транзакции"""
        return f"{self.get_transaction_type_display()} {self.amount} - {self.transaction_date.strftime('%d.%m.%Y')}"


class Budget(models.Model):
    """Модель бюджета"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='budgets',
        verbose_name='Пользователь'
    )
    budget_name = models.CharField(
        max_length=100,
        verbose_name='Название бюджета'
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Сумма'
    )
    period_type = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Ежедневный'),
            ('weekly', 'Еженедельный'),
            ('monthly', 'Ежемесячный'),
            ('yearly', 'Ежегодный'),
        ],
        verbose_name='Тип периода'
    )
    start_date = models.DateField(
        verbose_name='Дата начала'
    )
    end_date = models.DateField(
        verbose_name='Дата окончания',
        blank=True,
        null=True
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='budgets',
        verbose_name='Категория'
    )

    class Meta:
        verbose_name = 'Бюджет'
        verbose_name_plural = 'Бюджеты'
        ordering = ['-start_date']

    def __str__(self):
        """Возвращает строковое представление бюджета"""
        return f"{self.budget_name} - {self.amount} ({self.get_period_type_display()})"
