# Документация QuerySet для главной страницы проекта Topfer

## Описание виджетов главной страницы

### 1. Финансовый обзор
**Назначение**: Показать общую сумму на всех счетах пользователей

**QuerySet**:
```python
total_balance = Account.objects.aggregate(total=Sum('balance'))['total'] or 0
```
- **Агрегатная функция**: `Sum()` - суммирование балансов всех счетов
- **Ограничения**: Нет, выводится общая сумма
- **Логика**: Суммируются балансы всех счетов в системе

### 2. Топ-5 категорий расходов
**Назначение**: Показать самые популярные категории расходов по количеству транзакций

**QuerySet**:
```python
top_expense_categories = Category.objects.filter(
    category_type='expense'
).annotate(
    transaction_count=Count('transactions')
).order_by('-transaction_count')[:5]
```
- **filter()**: Фильтрация только категорий расходов (category_type='expense')
- **Агрегатная функция**: `Count()` - подсчет количества транзакций для каждой категории
- **order_by()**: Сортировка по убыванию количества транзакций
- **Ограничения**: Топ-5 категорий ([:5])
- **Логика**: Выводятся 5 категорий с наибольшим количеством транзакций

### 3. Последние транзакции
**Назначение**: Показать последние 10 транзакций в системе

**QuerySet**:
```python
recent_transactions = Transaction.objects.all().select_related(
    'account', 'category', 'account__currency'
).order_by('-transaction_date')[:10]
```
- **all()**: Выбор всех транзакций
- **select_related()**: Оптимизация запросов - предзагрузка связанных объектов
- **order_by()**: Сортировка по дате транзакции (от новых к старым)
- **Ограничения**: Последние 10 транзакций ([:10])
- **Логика**: Выводятся транзакции, отсортированные от новых к старым

### 4. Популярные счета
**Назначение**: Показать топ-5 счетов с наибольшим балансом

**QuerySet**:
```python
popular_accounts = Account.objects.all().select_related(
    'currency', 'user'
).order_by('-balance')[:5]
```
- **all()**: Выбор всех счетов
- **select_related()**: Оптимизация запросов
- **order_by()**: Сортировка по балансу (от большего к меньшему)
- **Ограничения**: Топ-5 счетов ([:5])
- **Логика**: Выводятся счета с наибольшими балансами

### 5. Активные бюджеты
**Назначение**: Показать текущие активные бюджеты

**QuerySet**:
```python
today = timezone.now().date()
active_budgets = Budget.objects.filter(
    Q(end_date__isnull=True) | Q(end_date__gte=today),
    start_date__lte=today
).select_related('user', 'category')[:5]
```
- **filter()**: Фильтрация бюджетов по условиям:
  - Бюджет без даты окончания (бессрочный) ИЛИ дата окончания >= сегодня
  - Дата начала <= сегодня
- **Q объекты**: Сложные логические условия (OR)
- **select_related()**: Оптимизация запросов
- **Ограничения**: Топ-5 активных бюджетов ([:5])
- **Логика**: Выводятся только активные на текущую дату бюджеты

### 6. Статистика за месяц - Доходы
**Назначение**: Показать общую сумму доходов за последние 30 дней

**QuerySet**:
```python
last_month = timezone.now() - timedelta(days=30)
monthly_income = Transaction.objects.filter(
    transaction_type='income',
    transaction_date__gte=last_month
).aggregate(total=Sum('amount'))['total'] or 0
```
- **filter()**: Фильтрация транзакций:
  - Тип = доход (income)
  - Дата >= 30 дней назад
- **Агрегатная функция**: `Sum()` - суммирование сумм транзакций
- **Ограничения**: Только за последние 30 дней
- **Логика**: Суммируются все доходы за период

### 7. Статистика за месяц - Расходы
**Назначение**: Показать общую сумму расходов за последние 30 дней

**QuerySet**:
```python
last_month = timezone.now() - timedelta(days=30)
monthly_expense = Transaction.objects.filter(
    transaction_type='expense',
    transaction_date__gte=last_month
).exclude(
    category__isnull=True
).aggregate(total=Sum('amount'))['total'] or 0
```
- **filter()**: Фильтрация транзакций:
  - Тип = расход (expense)
  - Дата >= 30 дней назад
- **exclude()**: Исключение транзакций без категории
- **Агрегатная функция**: `Sum()` - суммирование сумм транзакций
- **Ограничения**: Только за последние 30 дней, только с категорией
- **Логика**: Суммируются все расходы с категорией за период

### 8. Количество счетов
**QuerySet**:
```python
accounts_count = Account.objects.count()
```
- **Агрегатная функция**: `count()` - подсчет количества записей
- **Логика**: Подсчитывается общее количество счетов

### 9. Количество транзакций
**QuerySet**:
```python
transactions_count = Transaction.objects.count()
```
- **Агрегатная функция**: `count()` - подсчет количества записей
- **Логика**: Подсчитывается общее количество транзакций

## Поиск по транзакциям

**Назначение**: Поиск транзакций по описанию, категории или счету

**QuerySet**:
```python
results = Transaction.objects.filter(
    Q(description__icontains=query) |
    Q(category__category_name__icontains=query) |
    Q(account__account_name__icontains=query)
).select_related(
    'account', 'category', 'account__currency'
).distinct().order_by('-transaction_date')[:20]
```
- **filter()** с **Q объектами**: Поиск по нескольким полям (OR):
  - description__icontains - регистронезависимый поиск в описании
  - category__category_name__icontains - поиск в названии категории
  - account__account_name__icontains - поиск в названии счета
- **distinct()**: Убирает дубликаты
- **order_by()**: Сортировка по дате (от новых к старым)
- **Ограничения**: Максимум 20 результатов
- **Логика**: Поиск выполняется по всем указанным полям, результаты объединяются

## Аналитика - Расходы по категориям

**QuerySet**:
```python
expense_by_category = Category.objects.filter(
    category_type='expense'
).annotate(
    total_amount=Sum('transactions__amount'),
    count=Count('transactions')
).order_by('-total_amount')
```
- **filter()**: Только категории расходов
- **Агрегатные функции**:
  - `Sum()` - суммирование транзакций по категории
  - `Count()` - подсчет количества транзакций
- **order_by()**: Сортировка по сумме (от большей к меньшей)
- **Логика**: Для каждой категории расходов подсчитывается общая сумма и количество транзакций

## Таблицы базы данных, используемые на главной странице

1. **Account** (Счета) - баланс, тип счета, валюта
2. **Transaction** (Транзакции) - тип, сумма, дата, описание
3. **Category** (Категории) - название, тип, иконка
4. **Budget** (Бюджеты) - название, сумма, период
5. **User** (Пользователи) - email, имя
6. **Currency** (Валюты) - код, символ

Всего используется **6 таблиц** (требование >= 3 выполнено).
