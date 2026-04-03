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


class CategoryTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='Admin123!', role='admin')
        self.analyst = User.objects.create_user(username='analyst', password='Analyst123!', role='analyst')
        self.viewer = User.objects.create_user(username='viewer', password='Viewer123!', role='viewer')
        self.cat = Category.objects.create(name='Food')

    def test_any_user_can_list_categories(self):
        for user in (self.viewer, self.analyst, self.admin):
            resp = self.client.get('/api/transactions/categories/', **auth_header(user))
            self.assertEqual(resp.status_code, status.HTTP_200_OK, f'Failed for {user.role}')

    def test_unauthenticated_cannot_list_categories(self):
        resp = self.client.get('/api/transactions/categories/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_create_category(self):
        resp = self.client.post(
            '/api/transactions/categories/',
            {'name': 'Travel', 'description': 'Travel expenses'},
            format='json',
            **auth_header(self.admin),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_analyst_cannot_create_category(self):
        resp = self.client.post(
            '/api/transactions/categories/',
            {'name': 'Travel'},
            format='json',
            **auth_header(self.analyst),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_delete_category_with_transactions(self):
        Transaction.objects.create(
            user=self.analyst,
            amount=Decimal('10.00'),
            transaction_type='expense',
            category=self.cat,
            date=date.today(),
        )
        resp = self.client.delete(
            f'/api/transactions/categories/{self.cat.id}/',
            **auth_header(self.admin),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class TransactionCRUDTests(APITestCase):
    BASE = '/api/transactions/'

    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='Admin123!', role='admin')
        self.analyst = User.objects.create_user(username='analyst', password='Analyst123!', role='analyst')
        self.viewer = User.objects.create_user(username='viewer', password='Viewer123!', role='viewer')
        self.cat = Category.objects.create(name='Misc')
        self.txn = Transaction.objects.create(
            user=self.analyst,
            amount=Decimal('75.00'),
            transaction_type='expense',
            category=self.cat,
            date=date.today(),
            notes='Test transaction',
        )

    def _detail_url(self, txn):
        return f'{self.BASE}{txn.id}/'

    # ── Create ─────────────────────────────────────────────────────────────────

    def test_analyst_can_create_transaction(self):
        resp = self.client.post(
            self.BASE,
            {'amount': '200.00', 'transaction_type': 'income', 'date': str(date.today())},
            format='json',
            **auth_header(self.analyst),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['user_username'], 'analyst')

    def test_viewer_cannot_create_transaction(self):
        resp = self.client.post(
            self.BASE,
            {'amount': '50.00', 'transaction_type': 'income', 'date': str(date.today())},
            format='json',
            **auth_header(self.viewer),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_requires_auth(self):
        resp = self.client.post(
            self.BASE,
            {'amount': '50.00', 'transaction_type': 'income', 'date': str(date.today())},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Validation ─────────────────────────────────────────────────────────────

    def test_negative_amount_rejected(self):
        resp = self.client.post(
            self.BASE,
            {'amount': '-50.00', 'transaction_type': 'expense', 'date': str(date.today())},
            format='json',
            **auth_header(self.analyst),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zero_amount_rejected(self):
        resp = self.client.post(
            self.BASE,
            {'amount': '0.00', 'transaction_type': 'expense', 'date': str(date.today())},
            format='json',
            **auth_header(self.analyst),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_transaction_type_rejected(self):
        resp = self.client.post(
            self.BASE,
            {'amount': '50.00', 'transaction_type': 'savings', 'date': str(date.today())},
            format='json',
            **auth_header(self.analyst),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_date_rejected(self):
        resp = self.client.post(
            self.BASE,
            {'amount': '50.00', 'transaction_type': 'expense'},
            format='json',
            **auth_header(self.analyst),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Read ───────────────────────────────────────────────────────────────────

    def test_viewer_can_read_own_transactions(self):
        Transaction.objects.create(
            user=self.viewer, amount=Decimal('20'), transaction_type='income', date=date.today()
        )
        resp = self.client.get(self.BASE, **auth_header(self.viewer))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for txn in resp.data['results']:
            self.assertEqual(txn['user_username'], 'viewer')

    def test_users_cannot_see_each_others_transactions(self):
        other = User.objects.create_user(username='other', password='Other123!', role='analyst')
        resp = self.client.get(self.BASE, **auth_header(other))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 0)

    def test_admin_sees_all_transactions(self):
        Transaction.objects.create(
            user=self.viewer, amount=Decimal('10'), transaction_type='income', date=date.today()
        )
        resp = self.client.get(self.BASE, **auth_header(self.admin))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data['count'], 2)

    def test_analyst_cannot_access_other_analysts_transaction(self):
        other = User.objects.create_user(username='other', password='Other123!', role='analyst')
        resp = self.client.get(self._detail_url(self.txn), **auth_header(other))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ── Update ─────────────────────────────────────────────────────────────────

    def test_analyst_can_update_own_transaction(self):
        resp = self.client.patch(
            self._detail_url(self.txn),
            {'notes': 'Updated note'},
            format='json',
            **auth_header(self.analyst),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['notes'], 'Updated note')

    def test_viewer_cannot_update_own_transaction(self):
        viewer_txn = Transaction.objects.create(
            user=self.viewer, amount=Decimal('10'), transaction_type='income', date=date.today()
        )
        resp = self.client.patch(
            self._detail_url(viewer_txn),
            {'notes': 'Sneaky edit'},
            format='json',
            **auth_header(self.viewer),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_any_transaction(self):
        resp = self.client.patch(
            self._detail_url(self.txn),
            {'notes': 'Admin note'},
            format='json',
            **auth_header(self.admin),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # ── Delete ─────────────────────────────────────────────────────────────────

    def test_analyst_can_delete_own_transaction(self):
        txn = Transaction.objects.create(
            user=self.analyst, amount=Decimal('5'), transaction_type='expense', date=date.today()
        )
        resp = self.client.delete(self._detail_url(txn), **auth_header(self.analyst))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_viewer_cannot_delete_own_transaction(self):
        txn = Transaction.objects.create(
            user=self.viewer, amount=Decimal('5'), transaction_type='income', date=date.today()
        )
        resp = self.client.delete(self._detail_url(txn), **auth_header(self.viewer))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── Filtering ──────────────────────────────────────────────────────────────

    def test_filter_by_transaction_type(self):
        Transaction.objects.create(
            user=self.analyst, amount=Decimal('500'), transaction_type='income', date=date.today()
        )
        resp = self.client.get(self.BASE + '?transaction_type=income', **auth_header(self.analyst))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for txn in resp.data['results']:
            self.assertEqual(txn['transaction_type'], 'income')

    def test_filter_by_date_range(self):
        resp = self.client.get(
            f'{self.BASE}?date_from={date.today()}&date_to={date.today()}',
            **auth_header(self.analyst),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for txn in resp.data['results']:
            self.assertEqual(txn['date'], str(date.today()))

    def test_search_by_notes(self):
        Transaction.objects.create(
            user=self.analyst,
            amount=Decimal('30'),
            transaction_type='expense',
            date=date.today(),
            notes='coffee shop visit',
        )
        resp = self.client.get(self.BASE + '?search=coffee', **auth_header(self.analyst))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(resp.data['count'], 0)
