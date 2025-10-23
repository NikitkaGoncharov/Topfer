from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
import random
from finance.models import User, Currency, Category, Account, Tag, Transaction, Budget


class Command(BaseCommand):
    """Команда для заполнения базы данных тестовыми данными"""
    help = 'Populate database with test data'

    def handle(self, *args, **kwargs):
        """Основной метод выполнения команды - создает тестовые данные для всех моделей"""
        self.stdout.write('Creating test data...')

        # Создаем валюты
        currencies = [
            Currency.objects.get_or_create(
                currency_code='RUB',
                defaults={'currency_name': 'Российский рубль', 'symbol': '₽'}
            )[0],
            Currency.objects.get_or_create(
                currency_code='USD',
                defaults={'currency_name': 'Доллар США', 'symbol': '$'}
            )[0],
            Currency.objects.get_or_create(
                currency_code='EUR',
                defaults={'currency_name': 'Евро', 'symbol': '€'}
            )[0],
            Currency.objects.get_or_create(
                currency_code='GBP',
                defaults={'currency_name': 'Фунт стерлингов', 'symbol': '£'}
            )[0],
        ]
        self.stdout.write(self.style.SUCCESS(f'Created {len(currencies)} currencies'))

        # Создаем пользователей
        users_data = [
            {'email': 'ivan.petrov@example.com', 'first_name': 'Иван', 'last_name': 'Петров', 'subscription': 'premium'},
            {'email': 'maria.ivanova@example.com', 'first_name': 'Мария', 'last_name': 'Иванова', 'subscription': 'free'},
            {'email': 'alex.sidorov@example.com', 'first_name': 'Александр', 'last_name': 'Сидоров', 'subscription': 'business'},
            {'email': 'elena.kozlova@example.com', 'first_name': 'Елена', 'last_name': 'Козлова', 'subscription': 'premium'},
            {'email': 'dmitry.volkov@example.com', 'first_name': 'Дмитрий', 'last_name': 'Волков', 'subscription': 'free'},
        ]

        users = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults={
                    'password_hash': 'hashed_password_123',
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'subscription_type': user_data['subscription'],
                    'registration_date': timezone.now() - timedelta(days=random.randint(30, 365)),
                    'last_login': timezone.now() - timedelta(days=random.randint(0, 30)),
                }
            )
            users.append(user)
        self.stdout.write(self.style.SUCCESS(f'Created {len(users)} users'))

        # Создаем родительские категории
        parent_categories_data = [
            {'name': 'Продукты', 'type': 'expense', 'icon': '🛒', 'color': '#FF6B6B'},
            {'name': 'Транспорт', 'type': 'expense', 'icon': '🚗', 'color': '#4ECDC4'},
            {'name': 'Развлечения', 'type': 'expense', 'icon': '🎮', 'color': '#95E1D3'},
            {'name': 'Здоровье', 'type': 'expense', 'icon': '⚕️', 'color': '#F38181'},
            {'name': 'Зарплата', 'type': 'income', 'icon': '💰', 'color': '#6BCF7F'},
            {'name': 'Инвестиции', 'type': 'income', 'icon': '📈', 'color': '#5DA9E9'},
        ]

        parent_categories = {}
        for cat_data in parent_categories_data:
            cat, created = Category.objects.get_or_create(
                category_name=cat_data['name'],
                category_type=cat_data['type'],
                defaults={
                    'icon': cat_data['icon'],
                    'color': cat_data['color'],
                    'is_system': True,
                }
            )
            parent_categories[cat_data['name']] = cat

        # Создаем подкатегории
        subcategories_data = [
            {'name': 'Супермаркет', 'parent': 'Продукты', 'type': 'expense'},
            {'name': 'Рестораны', 'parent': 'Продукты', 'type': 'expense'},
            {'name': 'Такси', 'parent': 'Транспорт', 'type': 'expense'},
            {'name': 'Бензин', 'parent': 'Транспорт', 'type': 'expense'},
            {'name': 'Кино', 'parent': 'Развлечения', 'type': 'expense'},
            {'name': 'Игры', 'parent': 'Развлечения', 'type': 'expense'},
            {'name': 'Аптека', 'parent': 'Здоровье', 'type': 'expense'},
            {'name': 'Врачи', 'parent': 'Здоровье', 'type': 'expense'},
        ]

        all_categories = list(parent_categories.values())
        for sub_data in subcategories_data:
            cat, created = Category.objects.get_or_create(
                category_name=sub_data['name'],
                category_type=sub_data['type'],
                defaults={
                    'parent_category': parent_categories[sub_data['parent']],
                    'is_system': False,
                }
            )
            all_categories.append(cat)

        self.stdout.write(self.style.SUCCESS(f'Created {len(all_categories)} categories'))

        # Создаем счета для пользователей
        account_types = ['cash', 'card', 'bank', 'savings']
        accounts = []
        for user in users:
            for i in range(random.randint(2, 4)):
                account = Account.objects.create(
                    user=user,
                    account_name=f"{random.choice(['Основной', 'Зарплатный', 'Сберегательный', 'Карманные'])} {i+1}",
                    account_type=random.choice(account_types),
                    currency=random.choice(currencies),
                    balance=random.uniform(1000, 100000),
                    bank_connected=random.choice([True, False]),
                    created_date=timezone.now() - timedelta(days=random.randint(30, 365))
                )
                accounts.append(account)
        self.stdout.write(self.style.SUCCESS(f'Created {len(accounts)} accounts'))

        # Создаем теги
        tags_data = ['Работа', 'Личное', 'Срочно', 'Налоги', 'Подарки', 'Отпуск', 'Дети', 'Дом']
        all_tags = []
        for user in users:
            user_tags = []
            for tag_name in random.sample(tags_data, random.randint(3, 6)):
                tag, created = Tag.objects.get_or_create(
                    user=user,
                    tag_name=tag_name,
                    defaults={'color': f"#{random.randint(0, 0xFFFFFF):06x}"}
                )
                user_tags.append(tag)
                all_tags.append(tag)
        self.stdout.write(self.style.SUCCESS(f'Created {len(all_tags)} tags'))

        # Создаем транзакции
        transaction_count = 0
        for account in accounts:
            user_tags = Tag.objects.filter(user=account.user)
            # Создаем от 20 до 50 транзакций для каждого счета
            for _ in range(random.randint(20, 50)):
                trans_type = random.choice(['income', 'expense', 'expense', 'expense'])  # Больше расходов
                if trans_type == 'income':
                    category = random.choice([cat for cat in all_categories if cat.category_type == 'income'])
                else:
                    category = random.choice([cat for cat in all_categories if cat.category_type == 'expense'])

                transaction = Transaction.objects.create(
                    account=account,
                    category=category,
                    amount=random.uniform(100, 5000),
                    transaction_type=trans_type,
                    transaction_date=timezone.now() - timedelta(days=random.randint(0, 180)),
                    description=random.choice([
                        'Оплата за покупки',
                        'Покупка продуктов',
                        'Заправка автомобиля',
                        'Оплата счета',
                        'Перевод средств',
                        'Получение зарплаты',
                        'Возврат средств',
                        '',
                    ]),
                    is_recurring=random.choice([True, False, False, False]),
                )

                # Добавляем теги к некоторым транзакциям
                if user_tags and random.random() > 0.5:
                    transaction.tags.set(random.sample(list(user_tags), random.randint(1, min(3, len(user_tags)))))

                transaction_count += 1

        self.stdout.write(self.style.SUCCESS(f'Created {transaction_count} transactions'))

        # Создаем бюджеты
        budgets = []
        for user in users:
            for _ in range(random.randint(2, 5)):
                start_date = date.today() - timedelta(days=random.randint(0, 60))
                period_type = random.choice(['daily', 'weekly', 'monthly', 'yearly'])

                if period_type == 'daily':
                    end_date = start_date + timedelta(days=30)
                elif period_type == 'weekly':
                    end_date = start_date + timedelta(weeks=12)
                elif period_type == 'monthly':
                    end_date = start_date + timedelta(days=365)
                else:
                    end_date = start_date + timedelta(days=730)

                budget = Budget.objects.create(
                    user=user,
                    budget_name=random.choice([
                        'Бюджет на продукты',
                        'Транспортные расходы',
                        'Развлечения',
                        'Коммунальные услуги',
                        'Общий бюджет',
                    ]),
                    amount=random.uniform(5000, 50000),
                    period_type=period_type,
                    start_date=start_date,
                    end_date=end_date if random.random() > 0.2 else None,
                    category=random.choice(all_categories) if random.random() > 0.3 else None,
                )
                budgets.append(budget)

        self.stdout.write(self.style.SUCCESS(f'Created {len(budgets)} budgets'))

        self.stdout.write(self.style.SUCCESS('Test data created successfully!'))
        self.stdout.write(self.style.SUCCESS('You can now create a superuser with: python manage.py createsuperuser'))
