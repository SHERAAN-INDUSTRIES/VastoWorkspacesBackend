from django.conf import settings
from django.db import models


class VastoIdentity(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vasto_identity')
    issuer = models.URLField(max_length=512)
    subject = models.CharField(max_length=255)
    username = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('issuer', 'subject'), name='identity_issuer_subject_uniq')]

    def __str__(self):
        return f'{self.issuer} ({self.subject})'


class AuthorizationTransaction(models.Model):
    state = models.CharField(max_length=128, unique=True)
    nonce = models.CharField(max_length=128)
    code_verifier = models.CharField(max_length=128)
    session_key = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=('expires_at', 'consumed_at'))]
