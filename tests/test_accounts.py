from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


def auth_header(user):
    token = str(RefreshToken.for_user(user).access_token)
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


# ── Registration ───────────────────────────────────────────────────────────────

class RegistrationTests(APITestCase):
    URL = '/api/auth/register/'

    def _post(self, data):
        return self.client.post(self.URL, data, format='json')

    def test_register_creates_viewer_by_default(self):
        resp = self._post({
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'StrongPass1!',
            'password_confirm': 'StrongPass1!',
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(username='newuser').role, 'viewer')

    def test_register_returns_profile_data(self):
        resp = self._post({
            'username': 'alice',
            'password': 'StrongPass1!',
            'password_confirm': 'StrongPass1!',
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', resp.data)
        self.assertNotIn('password', resp.data)

    def test_register_password_mismatch_returns_400(self):
        resp = self._post({
            'username': 'bob',
            'password': 'StrongPass1!',
            'password_confirm': 'WrongPass1!',
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username_returns_400(self):
        User.objects.create_user(username='taken', password='pass12345')
        resp = self._post({
            'username': 'taken',
            'password': 'StrongPass1!',
            'password_confirm': 'StrongPass1!',
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password_returns_400(self):
        resp = self._post({
            'username': 'charlie',
            'password': 'short',
            'password_confirm': 'short',
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ── Authentication (JWT) ───────────────────────────────────────────────────────

class AuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='Pass12345!')

    def test_login_returns_tokens(self):
        resp = self.client.post('/api/auth/token/', {'username': 'user1', 'password': 'Pass12345!'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)

    def test_login_wrong_password_returns_401(self):
        resp = self.client.post('/api/auth/token/', {'username': 'user1', 'password': 'wrong'})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_unauthenticated_returns_401(self):
        resp = self.client.get('/api/auth/me/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_authenticated_returns_data(self):
        resp = self.client.get('/api/auth/me/', **auth_header(self.user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['username'], 'user1')

    def test_profile_does_not_expose_password(self):
        resp = self.client.get('/api/auth/me/', **auth_header(self.user))
        self.assertNotIn('password', resp.data)


# ── Role-based access on user management ──────────────────────────────────────

class UserManagementRoleTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='Admin123!', role='admin')
        self.analyst = User.objects.create_user(username='analyst', password='Analyst123!', role='analyst')
        self.viewer = User.objects.create_user(username='viewer', password='Viewer123!', role='viewer')

    def test_admin_can_list_users(self):
        resp = self.client.get('/api/auth/users/', **auth_header(self.admin))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_viewer_cannot_list_users(self):
        resp = self.client.get('/api/auth/users/', **auth_header(self.viewer))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_analyst_cannot_list_users(self):
        resp = self.client.get('/api/auth/users/', **auth_header(self.analyst))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_change_user_role(self):
        resp = self.client.patch(
            f'/api/auth/users/{self.viewer.id}/',
            {'role': 'analyst'},
            format='json',
            **auth_header(self.admin),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.viewer.refresh_from_db()
        self.assertEqual(self.viewer.role, 'analyst')

    def test_admin_cannot_delete_self(self):
        resp = self.client.delete(f'/api/auth/users/{self.admin.id}/', **auth_header(self.admin))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_deactivates_user(self):
        resp = self.client.delete(f'/api/auth/users/{self.viewer.id}/', **auth_header(self.admin))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.viewer.refresh_from_db()
        self.assertFalse(self.viewer.is_active)
