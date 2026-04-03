from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from transactions.models import Category, Transaction

User = get_user_model()


def auth_header(user):
    token = str(RefreshToken.for_user(user).access_token)
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


def make_txns(user, cat=None):
    """Create a simple pair of income/expense transactions for a user."""
    Transaction.objects.create(
        user=user, amount=Decimal('1000'), transaction_type='income',
        category=cat, date=date.today(),
    )
    Transaction.objects.create(
        user=user, amount=Decimal('300'), transaction_type='expense',
        category=cat, date=date.today(),
    )


class SummaryTests(APITestCase):
    URL = '/api/analytics/summary/'

    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='Admin123!', role='admin')
        self.analyst = User.objects.create_user(username='analyst', password='Analyst123!', role='analyst')
        self.viewer = User.objects.create_user(username='viewer', password='Viewer123!', role='viewer')
        self.cat = Category.objects.create(name='General')
        make_txns(self.analyst, self.cat)

    def test_viewer_can_access_summary(self):
        make_txns(self.viewer, self.cat)
        resp = self.client.get(self.URL, **auth_header(self.viewer))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_summary_correct_math(self):
        resp = self.client.get(self.URL, **auth_header(self.analyst))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(resp.data['total_income'])), Decimal('1000'))
        self.assertEqual(Decimal(str(resp.data['total_expenses'])), Decimal('300'))
        self.assertEqual(Decimal(str(resp.data['balance'])), Decimal('700'))

    def test_summary_only_shows_own_data(self):
        """Analyst should not see viewer's transactions in their summary."""
        make_txns(self.viewer)
        resp = self.client.get(self.URL, **auth_header(self.analyst))
        self.assertEqual(resp.data['transaction_count'], 2)

    def test_admin_sees_all_data(self):
        make_txns(self.viewer)
        resp = self.client.get(self.URL, **auth_header(self.admin))
        self.assertGreaterEqual(int(resp.data['transaction_count']), 4)

    def test_admin_can_filter_by_user(self):
        make_txns(self.viewer)
        resp = self.client.get(
            f'{self.URL}?user_id={self.viewer.id}',
            **auth_header(self.admin),
        )
        self.assertEqual(resp.data['transaction_count'], 2)

    def test_unauthenticated_returns_401(self):
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class CategoryBreakdownTests(APITestCase):
    URL = '/api/analytics/by-category/'

    def setUp(self):
        self.analyst = User.objects.create_user(username='analyst', password='Analyst123!', role='analyst')
        self.viewer = User.objects.create_user(username='viewer', password='Viewer123!', role='viewer')
        self.cat = Category.objects.create(name='Food')
        make_txns(self.analyst, self.cat)

    def test_analyst_can_access(self):
        resp = self.client.get(self.URL, **auth_header(self.analyst))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('overall', resp.data)
        self.assertIn('income_by_category', resp.data)
        self.assertIn('expense_by_category', resp.data)

    def test_viewer_is_forbidden(self):
        resp = self.client.get(self.URL, **auth_header(self.viewer))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_category_sums_are_correct(self):
        resp = self.client.get(self.URL, **auth_header(self.analyst))
        food_entry = next(
            (row for row in resp.data['overall'] if row['category_name'] == 'Food'), None
        )
        self.assertIsNotNone(food_entry)
        self.assertEqual(Decimal(str(food_entry['total'])), Decimal('1300'))


class MonthlyTotalsTests(APITestCase):
    URL = '/api/analytics/monthly/'

    def setUp(self):
        self.analyst = User.objects.create_user(username='analyst', password='Analyst123!', role='analyst')
        self.viewer = User.objects.create_user(username='viewer', password='Viewer123!', role='viewer')
        make_txns(self.analyst)

    def test_analyst_gets_monthly_data(self):
        resp = self.client.get(self.URL, **auth_header(self.analyst))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('year', resp.data)
        self.assertIn('months', resp.data)

    def test_viewer_is_forbidden(self):
        resp = self.client.get(self.URL, **auth_header(self.viewer))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_current_month_appears(self):
        resp = self.client.get(self.URL, **auth_header(self.analyst))
        current_month = date.today().strftime('%Y-%m')
        months = [m['month'] for m in resp.data['months']]
        self.assertIn(current_month, months)

    def test_custom_year_param(self):
        resp = self.client.get(f'{self.URL}?year=2020', **auth_header(self.analyst))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['year'], 2020)
        self.assertEqual(resp.data['months'], [])  # no data for 2020


class RecentActivityTests(APITestCase):
    URL = '/api/analytics/recent/'

    def setUp(self):
        self.analyst = User.objects.create_user(username='analyst', password='Analyst123!', role='analyst')
        self.viewer = User.objects.create_user(username='viewer', password='Viewer123!', role='viewer')
        make_txns(self.analyst)
        make_txns(self.viewer)

    def test_viewer_gets_only_own_recent(self):
        resp = self.client.get(self.URL, **auth_header(self.viewer))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for txn in resp.data:
            self.assertEqual(txn['user_username'], 'viewer')

    def test_default_limit_is_10(self):
        for _ in range(15):
            Transaction.objects.create(
                user=self.analyst, amount=Decimal('1'), transaction_type='income', date=date.today()
            )
        resp = self.client.get(self.URL, **auth_header(self.analyst))
        self.assertLessEqual(len(resp.data), 10)

    def test_custom_limit(self):
        for _ in range(5):
            Transaction.objects.create(
                user=self.analyst, amount=Decimal('1'), transaction_type='expense', date=date.today()
            )
        resp = self.client.get(f'{self.URL}?limit=3', **auth_header(self.analyst))
        self.assertEqual(len(resp.data), 3)

    def test_limit_capped_at_100(self):
        resp = self.client.get(f'{self.URL}?limit=999', **auth_header(self.analyst))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class ExportTests(APITestCase):
    URL = '/api/analytics/export/'

    def setUp(self):
        self.analyst = User.objects.create_user(username='analyst', password='Analyst123!', role='analyst')
        self.viewer = User.objects.create_user(username='viewer', password='Viewer123!', role='viewer')
        make_txns(self.analyst)

    def test_analyst_can_export_csv(self):
        resp = self.client.get(self.URL, **auth_header(self.analyst))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        self.assertIn('Content-Disposition', resp)

    def test_viewer_cannot_export(self):
        resp = self.client.get(self.URL, **auth_header(self.viewer))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_csv_contains_header_row(self):
        resp = self.client.get(self.URL, **auth_header(self.analyst))
        content = b''.join(resp.streaming_content).decode() if hasattr(resp, 'streaming_content') else resp.content.decode()
        self.assertIn('ID', content)
        self.assertIn('Amount', content)
        self.assertIn('Type', content)
