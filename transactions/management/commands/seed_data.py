import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from transactions.models import Category, Transaction

User = get_user_model()

CATEGORIES = [
    ('Salary', 'Regular employment income'),
    ('Freelance', 'Freelance and contract work'),
    ('Investment', 'Dividends, interest, capital gains'),
    ('Food', 'Groceries and dining out'),
    ('Transport', 'Fuel, public transit, ride-sharing'),
    ('Utilities', 'Electricity, water, internet, phone'),
    ('Entertainment', 'Streaming, events, hobbies'),
    ('Healthcare', 'Doctor visits, medications, gym'),
    ('Shopping', 'Clothing, electronics, household items'),
    ('Other', 'Miscellaneous'),
]

INCOME_CATEGORIES = ['Salary', 'Freelance', 'Investment']
EXPENSE_CATEGORIES = ['Food', 'Transport', 'Utilities', 'Entertainment', 'Healthcare', 'Shopping', 'Other']

USERS = [
    {'username': 'admin',   'password': 'admin123!',   'role': 'admin',   'email': 'admin@zorvyn.example',   'first_name': 'Alice',  'last_name': 'Admin'},
    {'username': 'analyst', 'password': 'analyst123!', 'role': 'analyst', 'email': 'analyst@zorvyn.example', 'first_name': 'Bob',    'last_name': 'Analyst'},
    {'username': 'viewer',  'password': 'viewer123!',  'role': 'viewer',  'email': 'viewer@zorvyn.example',  'first_name': 'Carol',  'last_name': 'Viewer'},
]


class Command(BaseCommand):
    help = 'Populate the database with sample users, categories, and transactions.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing transactions before seeding.',
        )

    def handle(self, *args, **options):
        if options['clear']:
            count, _ = Transaction.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {count} existing transactions.'))

        # ── Users ──────────────────────────────────────────────────────────────
        created_users = {}
        for spec in USERS:
            user, created = User.objects.get_or_create(
                username=spec['username'],
                defaults={
                    'email': spec['email'],
                    'role': spec['role'],
                    'first_name': spec['first_name'],
                    'last_name': spec['last_name'],
                },
            )
            user.set_password(spec['password'])
            user.save(update_fields=['password'])
            created_users[spec['username']] = user
            action = 'Created' if created else 'Updated'
            self.stdout.write(f'  {action} user: {user.username} ({user.role})')

        # ── Categories ─────────────────────────────────────────────────────────
        cat_objects = {}
        for name, description in CATEGORIES:
            cat, _ = Category.objects.get_or_create(name=name, defaults={'description': description})
            cat_objects[name] = cat
        self.stdout.write(f'  Ensured {len(cat_objects)} categories.')

        # ── Transactions (for analyst and viewer) ──────────────────────────────
        today = date.today()
        transactions_created = 0

        for username, config in [('analyst', {'days': 180, 'density': 2}), ('viewer', {'days': 60, 'density': 3})]:
            user = created_users[username]
            for i in range(config['days']):
                txn_date = today - timedelta(days=i)

                # Occasional payday (income)
                if i % 30 == 0:
                    Transaction.objects.create(
                        user=user,
                        amount=Decimal(str(random.randint(3000, 6000))),
                        transaction_type=Transaction.INCOME,
                        category=cat_objects['Salary'],
                        date=txn_date,
                        notes='Monthly salary payment',
                    )
                    transactions_created += 1

                if i % 45 == 5:
                    Transaction.objects.create(
                        user=user,
                        amount=Decimal(str(random.randint(200, 1500))),
                        transaction_type=Transaction.INCOME,
                        category=cat_objects[random.choice(['Freelance', 'Investment'])],
                        date=txn_date,
                        notes='Supplementary income',
                    )
                    transactions_created += 1

                # Daily expenses
                for _ in range(random.randint(0, config['density'])):
                    Transaction.objects.create(
                        user=user,
                        amount=Decimal(str(round(random.uniform(5, 250), 2))),
                        transaction_type=Transaction.EXPENSE,
                        category=cat_objects[random.choice(EXPENSE_CATEGORIES)],
                        date=txn_date,
                        notes='',
                    )
                    transactions_created += 1

        self.stdout.write(f'  Created {transactions_created} transactions.')

        self.stdout.write(self.style.SUCCESS('\nSeeding complete! Sample credentials:'))
        for spec in USERS:
            self.stdout.write(f'  {spec["username"]:10s} / {spec["password"]:15s}  role={spec["role"]}')
