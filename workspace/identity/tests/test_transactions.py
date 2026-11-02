import base64
import hashlib
from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone

from identity.models import AuthorizationTransaction
from identity.services.transactions import consume_transaction, create_transaction


class TransactionTests(TestCase):
    def test_pkce_s256_and_concurrent_transactions(self):
        first, challenge = create_transaction('session-a')
        second, _ = create_transaction('session-a')
        expected = base64.urlsafe_b64encode(hashlib.sha256(first.code_verifier.encode()).digest()).rstrip(b'=').decode()
        self.assertEqual(challenge, expected)
        self.assertNotEqual(first.state, second.state)
        self.assertEqual(AuthorizationTransaction.objects.count(), 2)

    def test_session_binding_expiry_and_single_use(self):
        item, _ = create_transaction('session-a')
        self.assertIsNone(consume_transaction(item.state, 'different-session'))
        item.expires_at = timezone.now() - timedelta(seconds=1)
        item.save(update_fields=('expires_at',))
        self.assertIsNone(consume_transaction(item.state, 'session-a'))

        item, _ = create_transaction('session-a')
        self.assertIsNotNone(consume_transaction(item.state, 'session-a'))
        self.assertIsNone(consume_transaction(item.state, 'session-a'))


class TransactionExpirySettingsTests(TestCase):
    @override_settings(IDENTITY_TRANSACTION_TTL_SECONDS=1)
    def test_short_transaction_ttl_is_applied(self):
        before = timezone.now()
        item, _ = create_transaction('s')
        self.assertLessEqual(item.expires_at, before + timedelta(seconds=2))
