from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from identity.models import AuthorizationTransaction, VastoIdentity
from identity.views import _get_or_create_user


class IdentityEndpointTests(TestCase):
    def test_app_initialization_and_discovery(self):
        from django.apps import apps
        self.assertTrue(apps.is_installed('identity'))
        from identity.services.vasto_oauth import validate_discovery_issuer
        with patch('identity.services.vasto_oauth.client') as oauth_client:
            oauth_client.return_value.load_server_metadata.return_value = {'issuer': 'expected'}
            with override_settings(VASTO_ISSUER='expected'):
                self.assertEqual(validate_discovery_issuer()['issuer'], 'expected')
            with override_settings(VASTO_ISSUER='wrong'):
                with self.assertRaises(RuntimeError):
                    validate_discovery_issuer()

    def test_start_creates_state_nonce_pkce_and_multiple_transactions(self):
        oauth_client = Mock()
        oauth_client.create_authorization_url.side_effect = [
            {'url': 'https://vasto.example/authorize?state=one'},
            {'url': 'https://vasto.example/authorize?state=two'},
        ]
        with patch('identity.views.client', return_value=oauth_client):
            one = self.client.get(reverse('vasto-start'))
            two = self.client.get(reverse('vasto-start'))
        self.assertEqual(one.status_code, 302)
        self.assertEqual(two.status_code, 302)
        self.assertEqual(AuthorizationTransaction.objects.count(), 2)
        args = [call.kwargs for call in oauth_client.create_authorization_url.call_args_list]
        self.assertTrue(args[0]['state'])
        self.assertTrue(args[0]['nonce'])
        self.assertEqual(args[0]['code_challenge_method'], 'S256')
        self.assertNotEqual(args[0]['state'], args[1]['state'])

    def test_state_mismatch_and_expired_transaction_rejected(self):
        with patch('identity.views.client') as oauth_client:
            oauth_client.return_value.create_authorization_url.return_value = {'url': 'https://vasto.example/auth'}
            self.client.get(reverse('vasto-start'))
        response = self.client.get(reverse('vasto-callback'), {'state': 'wrong', 'code': 'c'})
        self.assertEqual(response.status_code, 400)

    def test_first_time_identity_mapping_and_existing_mapping(self):
        claims = {'issuer': 'https://issuer.example', 'subject': 'subject-1', 'username': 'person', 'email': 'person@example.test', 'email_verified': True}
        user = _get_or_create_user(claims)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(VastoIdentity.objects.get().subject, 'subject-1')
        self.assertEqual(_get_or_create_user(claims).pk, user.pk)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_duplicate_issuer_subject_is_rejected_by_database(self):
        from django.db import IntegrityError, transaction
        user = get_user_model().objects.create_user(username='mapped-user')
        with self.assertRaises(IntegrityError), transaction.atomic():
            VastoIdentity.objects.create(user=user, issuer='iss', subject='same-subject')
            other = get_user_model().objects.create_user(username='other-user')
            VastoIdentity.objects.create(user=other, issuer='iss', subject='same-subject')

    def test_callback_maps_user_and_establishes_session(self):
        with patch('identity.views.client') as starter:
            starter.return_value.create_authorization_url.return_value = {'url': 'https://vasto.example/auth'}
            self.client.get(reverse('vasto-start'))
        item = AuthorizationTransaction.objects.get()
        with patch('identity.views.client') as oauth_client, patch('identity.views.validate_identity') as validate:
            oauth_client.return_value.load_server_metadata.return_value = {'issuer': 'http://127.0.0.1:8000/o'}
            oauth_client.return_value.fetch_access_token.return_value = {'access_token': 'secret'}
            validate.return_value = {'issuer': 'http://127.0.0.1:8000/o', 'subject': 'sub', 'username': 'alice', 'email': '', 'email_verified': False}
            with override_settings(WORKSPACES_FRONTEND_URL=''):
                result = self.client.get(reverse('vasto-callback'), {
                    'state': item.state, 'code': 'authorization-code',
                    'iss': 'http://127.0.0.1:8000/o',
                })
        self.assertEqual(result.status_code, 200)
        self.assertTrue('_auth_user_id' in self.client.session)
        self.assertEqual(VastoIdentity.objects.count(), 1)

    def test_callback_logs_safe_oauth_error_code(self):
        from authlib.integrations.base_client import OAuthError

        with patch('identity.views.client') as starter:
            starter.return_value.create_authorization_url.return_value = {'url': 'https://vasto.example/auth'}
            self.client.get(reverse('vasto-start'))
        item = AuthorizationTransaction.objects.get()
        with patch('identity.views.client') as oauth_client, self.assertLogs('identity.views', level='WARNING') as logs:
            oauth_client.return_value.load_server_metadata.return_value = {'issuer': 'http://127.0.0.1:8000/o'}
            oauth_client.return_value.fetch_access_token.side_effect = OAuthError(
                error='invalid_client', description='sensitive provider response',
            )
            result = self.client.get(reverse('vasto-callback'), {
                'state': item.state, 'code': 'authorization-code',
            })

        self.assertEqual(result.status_code, 401)
        self.assertIn('authorization code exchange', logs.output[0])
        self.assertIn('error=invalid_client', logs.output[0])
        self.assertNotIn('sensitive provider response', logs.output[0])

    def test_me_requires_auth_and_returns_approved_profile(self):
        self.assertEqual(self.client.get(reverse('auth-me')).status_code, 401)
        user = _get_or_create_user({'issuer': 'iss', 'subject': 'sub', 'username': 'alice', 'email': 'a@example.test', 'email_verified': True})
        self.client.force_login(user)
        response = self.client.get(reverse('auth-me'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'success')
        self.assertEqual(payload['user']['id'], user.pk)
        self.assertEqual(payload['user']['username'], 'alice')
        self.assertEqual(payload['user']['profile_picture'], None)
        self.assertIn('expires_at', payload['session'])
        self.assertNotIn('session_key', payload['session'])
        self.assertNotIn('subject', response.content.decode())

    def test_logout_requires_auth_and_terminates_session(self):
        path = reverse('auth-logout')
        self.assertEqual(self.client.post(path).status_code, 401)
        user = _get_or_create_user({'issuer': 'iss', 'subject': 'sub', 'username': 'alice', 'email': '', 'email_verified': False})
        self.client.force_login(user)
        self.assertEqual(self.client.post(path).status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_enforces_csrf(self):
        user = _get_or_create_user({'issuer': 'iss', 'subject': 'csrf-sub', 'username': 'alice', 'email': '', 'email_verified': False})
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(user)
        self.assertEqual(csrf_client.post(reverse('auth-logout')).status_code, 403)
