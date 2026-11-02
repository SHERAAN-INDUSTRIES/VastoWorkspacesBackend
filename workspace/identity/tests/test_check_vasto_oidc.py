import base64
import io
from unittest.mock import Mock, patch

from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, override_settings


@override_settings(
    VASTO_DISCOVERY_URL='http://127.0.0.1:8000/o/.well-known/openid-configuration',
    VASTO_ISSUER='http://127.0.0.1:8000/o',
    VASTO_CLIENT_ID='local-client',
    VASTO_CLIENT_SECRET='never-print-this',
    VASTO_REDIRECT_URI='http://127.0.0.1:8001/api/auth/vasto/callback/',
)
class VastoOIDCPreflightTests(SimpleTestCase):
    def setUp(self):
        self.metadata = {
            'issuer': 'http://127.0.0.1:8000/o',
            'authorization_endpoint': 'http://127.0.0.1:8000/o/authorize/',
            'token_endpoint': 'http://127.0.0.1:8000/o/token/',
            'userinfo_endpoint': 'http://127.0.0.1:8000/o/userinfo/',
            'jwks_uri': 'http://127.0.0.1:8000/o/.well-known/jwks.json',
        }
        self.jwks = {'keys': [{'kty': 'RSA', 'use': 'sig', 'alg': 'RS256', 'n': 'n', 'e': 'AQAB'}]}

    @patch('identity.management.commands.check_vasto_oidc.urllib.request.build_opener')
    @patch('identity.management.commands.check_vasto_oidc.get_json')
    def test_success_checks_jwks_and_uses_non_redirecting_authorization_probe(self, get_json, build_opener):
        get_json.side_effect = [self.metadata, self.jwks]
        response = Mock()
        response.status = 302
        response.headers = {'Location': 'http://127.0.0.1:8000/login/'}
        response.read.return_value = b''
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        token_response = Mock()
        token_response.status = 400
        token_response.read.return_value = b'{"error":"invalid_grant"}'
        token_response.__enter__ = Mock(return_value=token_response)
        token_response.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.side_effect = [response, token_response]
        build_opener.return_value = opener
        out = io.StringIO()
        call_command('check_vasto_oidc', stdout=out)
        self.assertIn('accepted client', out.getvalue())
        self.assertNotIn('never-print-this', out.getvalue())
        authorization_request = opener.open.call_args_list[0].args[0]
        token_request = opener.open.call_args_list[1].args[0]
        self.assertIn('code_challenge_method=S256', authorization_request.full_url)
        self.assertNotIn('never-print-this', authorization_request.full_url)
        self.assertIn('grant_type=authorization_code', token_request.data.decode())
        self.assertIn('never-print-this', base64.b64decode(token_request.get_header('Authorization').split()[1]).decode())

    @patch('identity.management.commands.check_vasto_oidc.get_json')
    def test_issuer_mismatch_has_specific_diagnostic(self, get_json):
        wrong = dict(self.metadata, issuer='http://wrong.example')
        get_json.side_effect = [wrong, self.jwks]
        with self.assertRaisesRegex(CommandError, 'issuer mismatch'):
            call_command('check_vasto_oidc', stdout=io.StringIO())

    @patch('identity.management.commands.check_vasto_oidc.get_json')
    def test_missing_credentials_are_reported_without_secrets(self, get_json):
        from django.test import override_settings as override
        get_json.side_effect = [self.metadata, self.jwks]
        with override(VASTO_CLIENT_ID='', VASTO_CLIENT_SECRET=''):
            with self.assertRaisesRegex(CommandError, 'VASTO_CLIENT_ID is missing'):
                call_command('check_vasto_oidc', stdout=io.StringIO())

    @patch('identity.management.commands.check_vasto_oidc.get_json')
    def test_missing_rsa_key_has_jwks_diagnostic(self, get_json):
        get_json.side_effect = [self.metadata, {'keys': []}]
        with self.assertRaisesRegex(CommandError, 'no usable RSA RS256 signing key'):
            call_command('check_vasto_oidc', stdout=io.StringIO())
