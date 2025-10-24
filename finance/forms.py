"""
Формы для аутентификации, регистрации пользователей и управления счетами
"""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Account, Currency, Budget, Category


class UserRegistrationForm(UserCreationForm):
    """
    Форма регистрации нового пользователя
    Расширяет стандартную форму Django дополнительными полями
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        }),
        label='Email'
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя пользователя'
        }),
        label='Имя пользователя'
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль'
        }),
        label='Пароль'
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Подтвердите пароль'
        }),
        label='Подтверждение пароля'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        """
        Проверяет уникальность email адреса

        Returns:
            str: Проверенный email

        Raises:
            ValidationError: Если email уже используется
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует')
        return email


class UserLoginForm(AuthenticationForm):
    """
    Форма входа пользователя в систему
    Расширяет стандартную форму Django с Bootstrap стилями
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя пользователя',
            'autofocus': True
        }),
        label='Имя пользователя'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль'
        }),
        label='Пароль'
    )


class AccountForm(forms.ModelForm):
    """
    Форма для создания и редактирования счета пользователя
    """
    account_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: Основной счет'
        }),
        label='Название счета'
    )
    account_type = forms.ChoiceField(
        choices=Account._meta.get_field('account_type').choices,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Тип счета'
    )
    currency = forms.ModelChoiceField(
        queryset=Currency.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Валюта'
    )
    balance = forms.DecimalField(
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        label='Начальный баланс'
    )
    bank_connected = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Подключен к банку'
    )

    class Meta:
        model = Account
        fields = ['account_name', 'account_type', 'currency', 'balance', 'bank_connected']

    def __init__(self, *args, **kwargs):
        """
        Инициализация формы
        Устанавливает начальное значение валюты
        """
        super().__init__(*args, **kwargs)
        # Устанавливаем рубль по умолчанию, если валюта существует
        if not self.instance.pk:
            try:
                rub = Currency.objects.get(currency_code='RUB')
                self.fields['currency'].initial = rub
            except Currency.DoesNotExist:
                pass


class BudgetForm(forms.ModelForm):
    """
    Форма для создания и редактирования бюджета пользователя
    """
    budget_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: Продукты на месяц'
        }),
        label='Название бюджета'
    )
    amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        label='Сумма'
    )
    period_type = forms.ChoiceField(
        choices=Budget._meta.get_field('period_type').choices,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Период'
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Категория',
        empty_label='Общий бюджет'
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Дата начала'
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Дата окончания',
        help_text='Оставьте пустым для бессрочного бюджета'
    )

    class Meta:
        model = Budget
        fields = ['budget_name', 'amount', 'period_type', 'category', 'start_date', 'end_date']

    def __init__(self, *args, **kwargs):
        """
        Инициализация формы
        Фильтрует категории расходов
        """
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Показываем только категории расходов
        self.fields['category'].queryset = Category.objects.filter(category_type='expense')
