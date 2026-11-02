from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from identity.services.oidc import validate_identity


@override_settings(VASTO_ISSUER='https://vasto.example')
class OIDCValidationTests(SimpleTestCase):
    def test_authlib_validates_id_token_with_nonce_and_expected_issuer(self):
        oauth_client = Mock()
        oauth_client.load_server_metadata.return_value = {'issuer': 'https://vasto.example'}
        oauth_client.parse_id_token.return_value = {'iss': 'https://vasto.example', 'sub': 'subject'}
        oauth_client.userinfo.return_value = {'sub': 'subject', 'preferred_username': 'alice', 'email': 'a@example.test', 'email_verified': True}
        with patch('identity.services.oidc.client', return_value=oauth_client):
            result = validate_identity({'id_token': 'signed-token', 'access_token': 'access-token'}, 'nonce-value')
        oauth_client.parse_id_token.assert_called_once_with(
            {'id_token': 'signed-token', 'access_token': 'access-token'},
            nonce='nonce-value', claims_options={'iss': {'values': ['https://vasto.example']}},
        )
        self.assertEqual(result['subject'], 'subject')
        self.assertEqual(set(result), {'issuer', 'subject', 'username', 'email', 'email_verified'})

    def test_signature_audience_expiry_and_nonce_validation_errors_are_not_bypassed(self):
        for failure in ('invalid signature', 'invalid audience', 'expired token', 'nonce mismatch'):
            with self.subTest(failure=failure):
                oauth_client = Mock()
                oauth_client.load_server_metadata.return_value = {'issuer': 'https://vasto.example'}
                oauth_client.parse_id_token.side_effect = ValueError(failure)
                with patch('identity.services.oidc.client', return_value=oauth_client):
                    with self.assertRaisesRegex(ValueError, failure):
                        validate_identity({'id_token': 'bad'}, 'expected-nonce')

    def test_invalid_discovery_issuer_and_userinfo_subject_mismatch_rejected(self):
        oauth_client = Mock()
        oauth_client.load_server_metadata.return_value = {'issuer': 'https://wrong.example'}
        with patch('identity.services.oidc.client', return_value=oauth_client):
            with self.assertRaisesRegex(ValueError, 'issuer mismatch'):
                validate_identity({'id_token': 'token'}, 'nonce')

        oauth_client.load_server_metadata.return_value = {'issuer': 'https://vasto.example'}
        oauth_client.parse_id_token.return_value = {'iss': 'https://vasto.example', 'sub': 'token-sub'}
        oauth_client.userinfo.return_value = {'sub': 'different-sub'}
        with patch('identity.services.oidc.client', return_value=oauth_client):
            with self.assertRaisesRegex(ValueError, 'subject does not match'):
                validate_identity({'id_token': 'token', 'access_token': 'access'}, 'nonce')
