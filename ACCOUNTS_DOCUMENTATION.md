# Документация страницы "Счета"

## Обзор
Страница "Счета" представляет собой полнофункциональную систему управления финансовыми счетами пользователя с возможностями создания, редактирования, просмотра и удаления счетов (CRUD операции).

## Архитектура

### 1. Модели данных (finance/models.py)

#### Account (Счет)
Основная модель для хранения информации о финансовых счетах:

```python
class Account(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Владелец счета
    account_name = models.CharField(max_length=100)           # Название счета
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)  # Тип счета
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)       # Валюта
    balance = models.DecimalField(max_digits=15, decimal_places=2)        # Баланс
    bank_connected = models.BooleanField(default=False)                   # Подключение к банку
    created_date = models.DateTimeField(auto_now_add=True)                # Дата создания
```

**Типы счетов:**
- `cash` - Наличные
- `card` - Банковская карта
- `bank` - Банковский счет
- `ewallet` - Электронный кошелек
- `investment` - Инвестиции
- `crypto` - Криптовалюта

### 2. Формы (finance/forms.py)

#### AccountForm
Форма для создания и редактирования счетов с использованием ModelForm:

```python
class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['account_name', 'account_type', 'currency', 'balance', 'bank_connected']
```

**Особенности:**
- Bootstrap классы для всех полей
- Автоматическая установка рубля (RUB) как валюты по умолчанию
- Валидация на уровне формы
- Плейсхолдеры и подсказки для пользователей

### 3. Представления (finance/views.py)

#### accounts(request) - Список счетов
**Назначение:** Отображает все счета текущего пользователя с группировкой по типам

**QuerySet операции:**
```python
# Фильтрация по пользователю
user_accounts = Account.objects.filter(user=request.user)
    .select_related('currency')
    .order_by('-created_date')

# Агрегация: подсчет общего баланса
total_balance = user_accounts.aggregate(total=Sum('balance'))['total'] or 0

# Группировка по типам счетов
accounts_by_type = {}
for account in user_accounts:
    acc_type = account.get_account_type_display()
    if acc_type not in accounts_by_type:
        accounts_by_type[acc_type] = []
    accounts_by_type[acc_type].append(account)
```

**Используемые QuerySet методы:**
- `filter()` - фильтрация по пользователю
- `select_related()` - оптимизация запросов (JOIN с таблицей Currency)
- `order_by()` - сортировка по дате создания (от новых к старым)
- `aggregate()` - агрегатная функция суммирования балансов
- `count()` - подсчет количества счетов

**Декоратор:** `@login_required` - доступ только для авторизованных пользователей

#### account_add(request) - Добавление счета
**Назначение:** Создание нового счета для текущего пользователя

**Логика:**
1. GET запрос: отображает пустую форму
2. POST запрос:
   - Валидирует данные формы
   - Сохраняет счет с привязкой к текущему пользователю
   - Выводит сообщение об успехе
   - Перенаправляет на страницу счетов

```python
@login_required
def account_add(request):
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user  # Привязка к пользователю
            account.save()
            messages.success(request, f'Счет "{account.account_name}" успешно создан!')
            return redirect('finance:accounts')
    else:
        form = AccountForm()
    return render(request, 'finance/account_form.html', {'form': form, 'title': 'Добавить новый счет'})
```

#### account_edit(request, pk) - Редактирование счета
**Назначение:** Изменение существующего счета пользователя

**Безопасность:**
- Использует `get_object_or_404()` для проверки существования
- Проверяет, что счет принадлежит текущему пользователю
- Возвращает 404 если счет не найден или принадлежит другому пользователю

```python
@login_required
def account_edit(request, pk):
    account = get_object_or_404(Account, pk=pk, user=request.user)

    if request.method == 'POST':
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, f'Счет "{account.account_name}" успешно обновлен!')
            return redirect('finance:accounts')
    else:
        form = AccountForm(instance=account)

    return render(request, 'finance/account_form.html', {
        'form': form,
        'title': 'Редактировать счет',
        'account': account
    })
```

#### account_delete(request, pk) - Удаление счета
**Назначение:** Удаление счета с подтверждением

**Особенности:**
- Требует подтверждения через POST запрос
- Показывает информацию о счете перед удалением
- Предупреждает об удалении связанных транзакций
- Использует каскадное удаление (on_delete=CASCADE)

```python
@login_required
def account_delete(request, pk):
    account = get_object_or_404(Account, pk=pk, user=request.user)

    if request.method == 'POST':
        account_name = account.account_name
        account.delete()
        messages.success(request, f'Счет "{account_name}" успешно удален!')
        return redirect('finance:accounts')

    return render(request, 'finance/account_confirm_delete.html', {'account': account})
```

### 4. URL маршруты (finance/urls.py)

```python
urlpatterns = [
    path('accounts/', views.accounts, name='accounts'),
    path('accounts/add/', views.account_add, name='account_add'),
    path('accounts/<int:pk>/edit/', views.account_edit, name='account_edit'),
    path('accounts/<int:pk>/delete/', views.account_delete, name='account_delete'),
]
```

**RESTful подход:**
- `/accounts/` - список всех счетов (READ)
- `/accounts/add/` - форма создания (CREATE)
- `/accounts/<pk>/edit/` - форма редактирования (UPDATE)
- `/accounts/<pk>/delete/` - подтверждение удаления (DELETE)

### 5. Шаблоны

#### accounts.html - Главная страница счетов
**Структура:**
- Левая колонка (8/12):
  - Список счетов с группировкой по типам
  - Карточки счетов с выпадающим меню действий
  - Пустое состояние (empty state) если нет счетов
- Правая колонка (4/12):
  - Общая статистика (количество счетов, общий баланс)
  - Быстрые действия (добавить счет, синхронизация, импорт)

**Особенности дизайна:**
- Адаптивная верстка Bootstrap 5
- Hover эффекты на карточках
- Иконки Bootstrap Icons
- Выпадающие меню для действий
- Отображение сообщений Django (messages framework)

**CSS анимации:**
```css
.account-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.15) !important;
}
```

#### account_form.html - Форма создания/редактирования
**Особенности:**
- Двухколоночная верстка для полей
- Валидация на стороне клиента (HTML5)
- Отображение ошибок для каждого поля
- Подсказки и плейсхолдеры
- Справочная информация о типах счетов
- Кнопки "Сохранить" и "Отмена"

#### account_confirm_delete.html - Подтверждение удаления
**Особенности:**
- Предупреждающий дизайн (warning colors)
- Полная информация о счете перед удалением
- Предупреждение о каскадном удалении транзакций
- Два действия: "Отмена" и "Да, удалить счет"

## Использование Django QuerySet API

### Примеры QuerySet операций на странице счетов:

1. **Фильтрация с связями (select_related):**
```python
Account.objects.filter(user=request.user).select_related('currency')
```
Одним запросом получает счета и их валюты через JOIN.

2. **Агрегатные функции:**
```python
user_accounts.aggregate(total=Sum('balance'))['total']
```
Вычисляет сумму всех балансов счетов.

3. **Сортировка:**
```python
order_by('-created_date')
```
Сортирует счета от новых к старым.

4. **Подсчет:**
```python
user_accounts.count()
```
Возвращает количество счетов пользователя.

5. **Безопасное получение объекта:**
```python
get_object_or_404(Account, pk=pk, user=request.user)
```
Получает объект или возвращает 404 ошибку.

## Безопасность

### Реализованные меры безопасности:

1. **Аутентификация:**
   - Декоратор `@login_required` на всех представлениях
   - Редирект на страницу входа для неавторизованных пользователей

2. **Авторизация:**
   - Фильтрация по `user=request.user` во всех запросах
   - Проверка владельца при редактировании/удалении
   - Невозможность доступа к чужим счетам

3. **CSRF защита:**
   - `{% csrf_token %}` во всех формах
   - Защита от подделки межсайтовых запросов

4. **Валидация данных:**
   - Django Form валидация на сервере
   - Проверка типов данных в модели
   - DecimalField для денежных сумм (точность до 2 знаков)

5. **SQL Injection защита:**
   - Использование Django ORM
   - Автоматическое экранирование параметров

## Интеграция с другими модулями

### Связи с другими моделями:

1. **User (django.contrib.auth.models.User):**
   - ForeignKey связь для владельца счета
   - CASCADE при удалении пользователя

2. **Currency:**
   - ForeignKey связь для валюты счета
   - PROTECT при попытке удаления используемой валюты

3. **Transaction:**
   - Обратная связь через ForeignKey в модели Transaction
   - CASCADE при удалении счета (удаляются все транзакции)

## Функциональные возможности

### Реализованные функции:

✅ Просмотр списка всех счетов пользователя
✅ Создание нового счета
✅ Редактирование существующего счета
✅ Удаление счета с подтверждением
✅ Группировка счетов по типам
✅ Отображение общей статистики
✅ Подсчет общего баланса по всем счетам
✅ Адаптивный дизайн для мобильных устройств
✅ Сообщения об успехе/ошибке операций
✅ Пустое состояние (empty state) для новых пользователей

### Планируемые функции:

⏳ Синхронизация с банком (API интеграция)
⏳ Импорт банковской выписки
⏳ История изменений баланса
⏳ Экспорт данных в CSV/Excel
⏳ Графики и аналитика по счетам

## Тестирование

### Сценарии тестирования:

1. **Создание счета:**
   - Открыть страницу добавления счета
   - Заполнить все обязательные поля
   - Нажать "Создать счет"
   - Проверить появление счета в списке

2. **Редактирование счета:**
   - Открыть меню действий на карточке счета
   - Выбрать "Редактировать"
   - Изменить название или баланс
   - Сохранить изменения
   - Проверить обновление данных

3. **Удаление счета:**
   - Открыть меню действий на карточке счета
   - Выбрать "Удалить"
   - Прочитать предупреждение
   - Подтвердить удаление
   - Проверить исчезновение счета из списка

4. **Безопасность:**
   - Попытка доступа без авторизации → редирект на /login/
   - Попытка редактировать чужой счет → 404 ошибка
   - Попытка удалить чужой счет → 404 ошибка

## Производительность

### Оптимизации:

1. **select_related('currency'):**
   - Уменьшает количество SQL запросов
   - JOIN вместо N+1 запросов

2. **Кэширование:**
   - Группировка счетов происходит в Python (не в БД)
   - Один запрос для получения всех счетов

3. **Ленивая загрузка:**
   - QuerySet выполняется только при обращении к данным

## Соответствие требованиям курсовой работы

### Использование Django QuerySet API:

✅ **filter()** - фильтрация счетов по пользователю
✅ **select_related()** - оптимизация запросов через JOIN
✅ **order_by()** - сортировка по дате создания
✅ **aggregate()** - агрегатная функция Sum для подсчета общего баланса
✅ **count()** - подсчет количества счетов
✅ **get_object_or_404()** - безопасное получение объекта

### CRUD операции:

✅ **CREATE** - создание новых счетов через AccountForm
✅ **READ** - чтение и отображение списка счетов
✅ **UPDATE** - редактирование существующих счетов
✅ **DELETE** - удаление счетов с подтверждением

### Безопасность:

✅ Аутентификация через `@login_required`
✅ Авторизация через фильтрацию `user=request.user`
✅ CSRF защита во всех формах
✅ Валидация данных на уровне форм и моделей

### Пользовательский интерфейс:

✅ Адаптивный дизайн Bootstrap 5
✅ Интуитивная навигация
✅ Информативные сообщения
✅ Подтверждение опасных действий (удаление)
✅ Справочная информация для пользователей

## Заключение

Страница "Счета" представляет собой полноценный модуль управления финансовыми счетами с использованием лучших практик Django:

- Использование Django ORM для работы с БД
- Применение Django Forms для валидации
- Декораторы для контроля доступа
- Messages framework для обратной связи
- Bootstrap для современного UI
- RESTful URL структура
- Безопасная работа с пользовательскими данными

Модуль полностью готов к использованию и может быть расширен дополнительными функциями (синхронизация с банками, импорт выписок, аналитика).
