from django.conf import settings
from django.db import models


class VastoIdentity(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vasto_identity')
    issuer = models.URLField(max_length=512)
    subject = models.CharField(max_length=255)
    username = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    email_verified = models.BooleanField(default=False)
    picture = models.URLField(max_length=2048, blank=True)
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


class UserProfileCache(models.Model):
    """Cached user profile from Pwaninet."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile_cache'
    )
    cached_data = models.JSONField(default=dict)
    last_synced_at = models.DateTimeField(auto_now=True)
    cache_expires_at = models.DateTimeField()
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('synced', 'Synced'),
            ('stale', 'Stale'),
            ('error', 'Error'),
        ],
        default='synced'
    )
    last_error = models.TextField(blank=True)

    class Meta:
        db_table = 'user_profile_cache'
        indexes = [
            models.Index(fields=['cache_expires_at']),
            models.Index(fields=['sync_status']),
        ]

    def __str__(self):
        return f'Profile cache for {self.user.username}'


class UserDocumentCache(models.Model):
    """Cached documents from Pwaninet."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_caches'
    )
    vasto_document_id = models.CharField(max_length=100)
    cached_data = models.JSONField(default=dict)
    last_synced_at = models.DateTimeField(auto_now=True)
    cache_expires_at = models.DateTimeField()
    sync_status = models.CharField(max_length=20, default='synced')

    class Meta:
        db_table = 'user_document_cache'
        unique_together = [['user', 'vasto_document_id']]
        indexes = [
            models.Index(fields=['cache_expires_at']),
            models.Index(fields=['vasto_document_id']),
        ]

    def __str__(self):
        return f'Document cache {self.vasto_document_id} for {self.user.username}'


class UserInstitutionCache(models.Model):
    """Cached institution data from Pwaninet."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='institution_cache'
    )
    vasto_institution_id = models.CharField(max_length=100)
    cached_data = models.JSONField(default=dict)
    last_synced_at = models.DateTimeField(auto_now=True)
    cache_expires_at = models.DateTimeField()
    sync_status = models.CharField(max_length=20, default='synced')

    class Meta:
        db_table = 'user_institution_cache'
        indexes = [
            models.Index(fields=['cache_expires_at']),
        ]

    def __str__(self):
        return f'Institution cache for {self.user.username}'


class UserChatCache(models.Model):
    """Cached chat history from Pwaninet."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_caches'
    )
    workspace_id = models.CharField(max_length=100, blank=True)
    cached_messages = models.JSONField(default=list)
    last_synced_at = models.DateTimeField(auto_now=True)
    cache_expires_at = models.DateTimeField()
    last_message_id = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'user_chat_cache'
        unique_together = [['user', 'workspace_id']]
        indexes = [
            models.Index(fields=['cache_expires_at']),
        ]

    def __str__(self):
        return f'Chat cache for {self.user.username}'


class UserCourseCache(models.Model):
    """Cached courses from Pwaninet."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='course_caches'
    )
    vasto_course_id = models.CharField(max_length=100)
    cached_data = models.JSONField(default=dict)
    last_synced_at = models.DateTimeField(auto_now=True)
    cache_expires_at = models.DateTimeField()
    sync_status = models.CharField(max_length=20, default='synced')

    class Meta:
        db_table = 'user_course_cache'
        unique_together = [['user', 'vasto_course_id']]
        indexes = [
            models.Index(fields=['cache_expires_at']),
        ]

    def __str__(self):
        return f'Course cache {self.vasto_course_id} for {self.user.username}'


class UserGroupCache(models.Model):
    """Cached groups from Pwaninet."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_caches'
    )
    vasto_group_id = models.CharField(max_length=100)
    cached_data = models.JSONField(default=dict)
    last_synced_at = models.DateTimeField(auto_now=True)
    cache_expires_at = models.DateTimeField()
    sync_status = models.CharField(max_length=20, default='synced')

    class Meta:
        db_table = 'user_group_cache'
        unique_together = [['user', 'vasto_group_id']]
        indexes = [
            models.Index(fields=['cache_expires_at']),
        ]

    def __str__(self):
        return f'Group cache {self.vasto_group_id} for {self.user.username}'


class UserNotificationCache(models.Model):
    """Cached notifications from Pwaninet."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_caches'
    )
    vasto_notification_id = models.CharField(max_length=100)
    cached_data = models.JSONField(default=dict)
    last_synced_at = models.DateTimeField(auto_now=True)
    cache_expires_at = models.DateTimeField()
    is_read = models.BooleanField(default=False)
    sync_status = models.CharField(max_length=20, default='synced')

    class Meta:
        db_table = 'user_notification_cache'
        unique_together = [['user', 'vasto_notification_id']]
        indexes = [
            models.Index(fields=['cache_expires_at']),
            models.Index(fields=['is_read']),
        ]

    def __str__(self):
        return f'Notification cache {self.vasto_notification_id} for {self.user.username}'


class UserConversationCache(models.Model):
    """Cached conversations from Pwaninet."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversation_caches'
    )
    vasto_conversation_id = models.CharField(max_length=100)
    cached_data = models.JSONField(default=dict)
    cached_messages = models.JSONField(default=list)
    last_synced_at = models.DateTimeField(auto_now=True)
    cache_expires_at = models.DateTimeField()
    last_message_id = models.CharField(max_length=100, blank=True)
    unread_count = models.IntegerField(default=0)
    sync_status = models.CharField(max_length=20, default='synced')

    class Meta:
        db_table = 'user_conversation_cache'
        unique_together = [['user', 'vasto_conversation_id']]
        indexes = [
            models.Index(fields=['cache_expires_at']),
        ]

    def __str__(self):
        return f'Conversation cache {self.vasto_conversation_id} for {self.user.username}'


class SyncLog(models.Model):
    """Log of sync operations for monitoring."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sync_logs',
        null=True,
        blank=True
    )
    sync_type = models.CharField(
        max_length=20,
        choices=[
            ('profile', 'Profile'),
            ('documents', 'Documents'),
            ('institution', 'Institution'),
            ('chat', 'Chat'),
            ('courses', 'Courses'),
            ('groups', 'Groups'),
            ('notifications', 'Notifications'),
            ('conversations', 'Conversations'),
            ('full', 'Full Sync'),
        ]
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('partial', 'Partial'),
            ('error', 'Error'),
        ]
    )
    items_synced = models.IntegerField(default=0)
    duration_ms = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    triggered_by = models.CharField(
        max_length=20,
        choices=[
            ('user', 'User Request'),
            ('scheduled', 'Scheduled Task'),
            ('callback', 'OAuth Callback'),
        ],
        default='user'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sync_log'
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['sync_type', 'status']),
        ]

    def __str__(self):
        return f'{self.sync_type} sync for {self.user.username if self.user else "all"} - {self.status}'
