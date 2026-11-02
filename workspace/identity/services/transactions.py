import base64
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from identity.models import AuthorizationTransaction


def create_transaction(session_key):
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    now = timezone.now()
    item = AuthorizationTransaction.objects.create(
        state=secrets.token_urlsafe(32), nonce=secrets.token_urlsafe(32),
        code_verifier=verifier, session_key=session_key,
        expires_at=now + timedelta(seconds=settings.IDENTITY_TRANSACTION_TTL_SECONDS),
    )
    return item, challenge


def consume_transaction(state, session_key):
    now = timezone.now()
    with transaction.atomic():
        item = AuthorizationTransaction.objects.select_for_update().filter(
            state=state, session_key=session_key, consumed_at__isnull=True, expires_at__gt=now,
        ).first()
        if item is None:
            return None
        item.consumed_at = now
        item.save(update_fields=('consumed_at',))
        return item


def cleanup_expired_transactions():
    return AuthorizationTransaction.objects.filter(expires_at__lte=timezone.now()).delete()
