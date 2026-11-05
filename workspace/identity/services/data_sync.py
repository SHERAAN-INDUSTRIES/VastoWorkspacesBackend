"""Data sync service for fetching and caching user data from Pwaninet."""
import logging
from datetime import timedelta
from typing import Optional

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from identity.models import (
    UserProfileCache,
    UserDocumentCache,
    UserInstitutionCache,
    UserChatCache,
    UserCourseCache,
    UserProgrammeCache,
    UserGroupCache,
    UserNotificationCache,
    UserConversationCache,
    SyncLog,
)

logger = logging.getLogger(__name__)

User = get_user_model()


class DataSyncService:
    """Service for synchronizing user data from Pwaninet to Workspaces cache."""

    def __init__(self):
        self.base_url = settings.VASTO_API_BASE_URL
        self.service_token = settings.VASTO_SERVICE_TOKEN
        self.timeout = 30  # seconds

    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        return {
            'Authorization': f'Token {self.service_token}',
            'Content-Type': 'application/json',
        }

    def _get_vasto_user_id(self, user) -> Optional[int]:
        """Get the Pwaninet user ID from Workspaces user."""
        try:
            identity = user.vasto_identity
            return int(identity.subject)  # OIDC subject is the user ID
        except Exception as e:
            logger.error(f"Failed to get Vasto user ID for {user.username}: {e}")
            return None

    def _fetch_from_pwaninet(self, endpoint: str, vasto_user_id: int) -> Optional[dict]:
        """Fetch data from Pwaninet internal API."""
        url = f"{self.base_url}/users/api/internal/users/{vasto_user_id}/{endpoint}/"
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching {endpoint} for user {vasto_user_id}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {endpoint} for user {vasto_user_id}: {e}")
            return None

    def _log_sync(self, user, sync_type: str, status: str, items_synced: int = 0, error: str = '', triggered_by: str = 'user'):
        """Log sync operation."""
        try:
            SyncLog.objects.create(
                user=user,
                sync_type=sync_type,
                status=status,
                items_synced=items_synced,
                error_message=error,
                triggered_by=triggered_by,
            )
        except Exception as e:
            logger.error(f"Failed to log sync: {e}")

    def sync_user_profile(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> bool:
        """Sync user profile from Pwaninet."""
        vasto_user_id = self._get_vasto_user_id(user)
        if not vasto_user_id:
            self._log_sync(user, 'profile', 'error', error='No Vasto user ID', triggered_by=triggered_by)
            return False

        # Check cache
        if not force_refresh:
            cache_key = f"profile:{user.id}"
            cached = cache.get(cache_key)
            if cached:
                return True

        data = self._fetch_from_pwaninet('profile', vasto_user_id)
        if not data:
            self._log_sync(user, 'profile', 'error', error='Failed to fetch from Pwaninet', triggered_by=triggered_by)
            return False

        # Update cache
        try:
            cache_expires = timezone.now() + timedelta(seconds=settings.CACHE_PROFILE_TTL)
            UserProfileCache.objects.update_or_create(
                user=user,
                defaults={
                    'cached_data': data,
                    'cache_expires_at': cache_expires,
                    'sync_status': 'synced',
                    'last_error': '',
                }
            )
            cache.set(f"profile:{user.id}", data, timeout=settings.CACHE_PROFILE_TTL)
            self._log_sync(user, 'profile', 'success', items_synced=1, triggered_by=triggered_by)
            return True
        except Exception as e:
            logger.error(f"Failed to cache profile for {user.username}: {e}")
            self._log_sync(user, 'profile', 'error', error=str(e), triggered_by=triggered_by)
            return False

    def get_user_profile(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> Optional[dict]:
        """Get user profile from cache or sync if needed."""
        # Try cache first
        cache_key = f"profile:{user.id}"
        cached = cache.get(cache_key)
        if cached and not force_refresh:
            return cached

        # Try database cache
        try:
            profile_cache = UserProfileCache.objects.get(user=user)
            if profile_cache.cache_expires_at > timezone.now() and not force_refresh:
                return profile_cache.cached_data
        except UserProfileCache.DoesNotExist:
            pass

        # Sync from Pwaninet
        if self.sync_user_profile(user, force_refresh=True, triggered_by=triggered_by):
            return cache.get(cache_key) or UserProfileCache.objects.get(user=user).cached_data
        return None

    def sync_user_documents(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> bool:
        """Sync user documents from Pwaninet."""
        vasto_user_id = self._get_vasto_user_id(user)
        if not vasto_user_id:
            self._log_sync(user, 'documents', 'error', error='No Vasto user ID', triggered_by=triggered_by)
            return False

        data = self._fetch_from_pwaninet('documents', vasto_user_id)
        if not data:
            self._log_sync(user, 'documents', 'error', error='Failed to fetch from Pwaninet', triggered_by=triggered_by)
            return False

        documents = data.get('documents', [])
        cache_expires = timezone.now() + timedelta(seconds=settings.CACHE_DOCUMENTS_TTL)

        try:
            # Clear existing cache for this user
            UserDocumentCache.objects.filter(user=user).delete()

            # Cache each document
            for doc in documents:
                UserDocumentCache.objects.create(
                    user=user,
                    vasto_document_id=str(doc.get('id', '')),
                    cached_data=doc,
                    cache_expires_at=cache_expires,
                )

            cache.set(f"documents:{user.id}", documents, timeout=settings.CACHE_DOCUMENTS_TTL)
            self._log_sync(user, 'documents', 'success', items_synced=len(documents), triggered_by=triggered_by)
            return True
        except Exception as e:
            logger.error(f"Failed to cache documents for {user.username}: {e}")
            self._log_sync(user, 'documents', 'error', error=str(e), triggered_by=triggered_by)
            return False

    def get_user_documents(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> Optional[list]:
        """Get user documents from cache or sync if needed."""
        cache_key = f"documents:{user.id}"
        cached = cache.get(cache_key)
        if cached and not force_refresh:
            return cached

        # Try database cache
        try:
            docs = UserDocumentCache.objects.filter(
                user=user,
                cache_expires_at__gt=timezone.now()
            ).values_list('cached_data', flat=True)
            if docs and not force_refresh:
                return list(docs)
        except Exception:
            pass

        # Sync from Pwaninet
        if self.sync_user_documents(user, force_refresh=True, triggered_by=triggered_by):
            return cache.get(cache_key)
        return []

    def sync_user_institution(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> bool:
        """Sync user institution from Pwaninet."""
        vasto_user_id = self._get_vasto_user_id(user)
        if not vasto_user_id:
            self._log_sync(user, 'institution', 'error', error='No Vasto user ID', triggered_by=triggered_by)
            return False

        data = self._fetch_from_pwaninet('institution', vasto_user_id)
        if not data:
            self._log_sync(user, 'institution', 'error', error='Failed to fetch from Pwaninet', triggered_by=triggered_by)
            return False

        try:
            cache_expires = timezone.now() + timedelta(seconds=settings.CACHE_INSTITUTION_TTL)
            UserInstitutionCache.objects.update_or_create(
                user=user,
                defaults={
                    'vasto_institution_id': str(data.get('id', '')),
                    'cached_data': data,
                    'cache_expires_at': cache_expires,
                    'sync_status': 'synced',
                }
            )
            cache.set(f"institution:{user.id}", data, timeout=settings.CACHE_INSTITUTION_TTL)
            self._log_sync(user, 'institution', 'success', items_synced=1, triggered_by=triggered_by)
            return True
        except Exception as e:
            logger.error(f"Failed to cache institution for {user.username}: {e}")
            self._log_sync(user, 'institution', 'error', error=str(e), triggered_by=triggered_by)
            return False

    def get_user_institution(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> Optional[dict]:
        """Get user institution from cache or sync if needed."""
        cache_key = f"institution:{user.id}"
        cached = cache.get(cache_key)
        if cached and not force_refresh:
            return cached

        try:
            inst_cache = UserInstitutionCache.objects.get(user=user)
            if inst_cache.cache_expires_at > timezone.now() and not force_refresh:
                return inst_cache.cached_data
        except UserInstitutionCache.DoesNotExist:
            pass

        if self.sync_user_institution(user, force_refresh=True, triggered_by=triggered_by):
            return cache.get(cache_key) or UserInstitutionCache.objects.get(user=user).cached_data
        return None

    def sync_user_courses(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> bool:
        """Sync user courses from Pwaninet."""
        vasto_user_id = self._get_vasto_user_id(user)
        if not vasto_user_id:
            self._log_sync(user, 'courses', 'error', error='No Vasto user ID', triggered_by=triggered_by)
            return False

        data = self._fetch_from_pwaninet('courses', vasto_user_id)
        if not data:
            self._log_sync(user, 'courses', 'error', error='Failed to fetch from Pwaninet', triggered_by=triggered_by)
            return False

        courses = data.get('courses', [])
        cache_expires = timezone.now() + timedelta(seconds=settings.CACHE_COURSES_TTL)

        try:
            UserCourseCache.objects.filter(user=user).delete()
            for course in courses:
                UserCourseCache.objects.create(
                    user=user,
                    vasto_course_id=str(course.get('id', '')),
                    cached_data=course,
                    cache_expires_at=cache_expires,
                )

            cache.set(f"courses:{user.id}", courses, timeout=settings.CACHE_COURSES_TTL)
            self._log_sync(user, 'courses', 'success', items_synced=len(courses), triggered_by=triggered_by)
            return True
        except Exception as e:
            logger.error(f"Failed to cache courses for {user.username}: {e}")
            self._log_sync(user, 'courses', 'error', error=str(e), triggered_by=triggered_by)
            return False

    def get_user_courses(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> Optional[list]:
        """Get user courses from cache or sync if needed."""
        cache_key = f"courses:{user.id}"
        cached = cache.get(cache_key)
        if cached and not force_refresh:
            return cached

        try:
            courses = UserCourseCache.objects.filter(
                user=user,
                cache_expires_at__gt=timezone.now()
            ).values_list('cached_data', flat=True)
            if courses and not force_refresh:
                return list(courses)
        except Exception:
            pass

        if self.sync_user_courses(user, force_refresh=True, triggered_by=triggered_by):
            return cache.get(cache_key)
        return []

    def sync_user_programmes(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> bool:
        """Sync user programmes from Pwaninet."""
        vasto_user_id = self._get_vasto_user_id(user)
        if not vasto_user_id:
            self._log_sync(user, 'programmes', 'error', error='No Vasto user ID', triggered_by=triggered_by)
            return False

        data = self._fetch_from_pwaninet('programmes', vasto_user_id)
        if not data:
            self._log_sync(user, 'programmes', 'error', error='Failed to fetch from Pwaninet', triggered_by=triggered_by)
            return False

        programmes = data.get('programmes', [])
        cache_expires = timezone.now() + timedelta(seconds=settings.CACHE_PROGRAMMES_TTL)

        try:
            UserProgrammeCache.objects.filter(user=user).delete()
            for programme in programmes:
                UserProgrammeCache.objects.create(
                    user=user,
                    vasto_programme_id=str(programme.get('id', '')),
                    cached_data=programme,
                    cache_expires_at=cache_expires,
                )

            cache.set(f"programmes:{user.id}", data, timeout=settings.CACHE_PROGRAMMES_TTL)
            self._log_sync(user, 'programmes', 'success', items_synced=len(programmes), triggered_by=triggered_by)
            return True
        except Exception as e:
            logger.error(f"Failed to cache programmes for {user.username}: {e}")
            self._log_sync(user, 'programmes', 'error', error=str(e), triggered_by=triggered_by)
            return False

    def get_user_programmes(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> Optional[dict]:
        """Get user programmes from cache or sync if needed."""
        cache_key = f"programmes:{user.id}"
        cached = cache.get(cache_key)
        if cached and not force_refresh:
            return cached

        try:
            rows = UserProgrammeCache.objects.filter(
                user=user,
                cache_expires_at__gt=timezone.now()
            ).values_list('cached_data', flat=True)
            programmes = list(rows)
            if programmes and not force_refresh:
                current_id = next(
                    (p.get('id') for p in programmes if p.get('is_current')),
                    programmes[0].get('id') if programmes else None,
                )
                return {'programmes': programmes, 'current_programme_id': current_id}
        except Exception:
            pass

        if self.sync_user_programmes(user, force_refresh=True, triggered_by=triggered_by):
            return cache.get(cache_key)
        return {'programmes': [], 'current_programme_id': None}

    def sync_user_groups(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> bool:
        """Sync user groups from Pwaninet."""
        vasto_user_id = self._get_vasto_user_id(user)
        if not vasto_user_id:
            self._log_sync(user, 'groups', 'error', error='No Vasto user ID', triggered_by=triggered_by)
            return False

        data = self._fetch_from_pwaninet('groups', vasto_user_id)
        if not data:
            self._log_sync(user, 'groups', 'error', error='Failed to fetch from Pwaninet', triggered_by=triggered_by)
            return False

        groups = data.get('groups', [])
        cache_expires = timezone.now() + timedelta(seconds=settings.CACHE_GROUPS_TTL)

        try:
            UserGroupCache.objects.filter(user=user).delete()
            for group in groups:
                UserGroupCache.objects.create(
                    user=user,
                    vasto_group_id=str(group.get('id', '')),
                    cached_data=group,
                    cache_expires_at=cache_expires,
                )

            cache.set(f"groups:{user.id}", groups, timeout=settings.CACHE_GROUPS_TTL)
            self._log_sync(user, 'groups', 'success', items_synced=len(groups), triggered_by=triggered_by)
            return True
        except Exception as e:
            logger.error(f"Failed to cache groups for {user.username}: {e}")
            self._log_sync(user, 'groups', 'error', error=str(e), triggered_by=triggered_by)
            return False

    def get_user_groups(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> Optional[list]:
        """Get user groups from cache or sync if needed."""
        cache_key = f"groups:{user.id}"
        cached = cache.get(cache_key)
        if cached and not force_refresh:
            return cached

        try:
            groups = UserGroupCache.objects.filter(
                user=user,
                cache_expires_at__gt=timezone.now()
            ).values_list('cached_data', flat=True)
            if groups and not force_refresh:
                return list(groups)
        except Exception:
            pass

        if self.sync_user_groups(user, force_refresh=True, triggered_by=triggered_by):
            return cache.get(cache_key)
        return []

    def sync_user_notifications(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> bool:
        """Sync user notifications from Pwaninet."""
        vasto_user_id = self._get_vasto_user_id(user)
        if not vasto_user_id:
            self._log_sync(user, 'notifications', 'error', error='No Vasto user ID', triggered_by=triggered_by)
            return False

        data = self._fetch_from_pwaninet('notifications', vasto_user_id)
        if not data:
            self._log_sync(user, 'notifications', 'error', error='Failed to fetch from Pwaninet', triggered_by=triggered_by)
            return False

        notifications = data.get('notifications', [])
        cache_expires = timezone.now() + timedelta(seconds=settings.CACHE_NOTIFICATIONS_TTL)

        try:
            UserNotificationCache.objects.filter(user=user).delete()
            for notif in notifications:
                UserNotificationCache.objects.create(
                    user=user,
                    vasto_notification_id=str(notif.get('id', '')),
                    cached_data=notif,
                    cache_expires_at=cache_expires,
                    is_read=notif.get('is_read', False),
                )

            cache.set(f"notifications:{user.id}", notifications, timeout=settings.CACHE_NOTIFICATIONS_TTL)
            self._log_sync(user, 'notifications', 'success', items_synced=len(notifications), triggered_by=triggered_by)
            return True
        except Exception as e:
            logger.error(f"Failed to cache notifications for {user.username}: {e}")
            self._log_sync(user, 'notifications', 'error', error=str(e), triggered_by=triggered_by)
            return False

    def get_user_notifications(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> Optional[list]:
        """Get user notifications from cache or sync if needed."""
        cache_key = f"notifications:{user.id}"
        cached = cache.get(cache_key)
        if cached and not force_refresh:
            return cached

        try:
            notifs = UserNotificationCache.objects.filter(
                user=user,
                cache_expires_at__gt=timezone.now()
            ).order_by('-cached_data__created_at')
            if notifs and not force_refresh:
                return [n.cached_data for n in notifs]
        except Exception:
            pass

        if self.sync_user_notifications(user, force_refresh=True, triggered_by=triggered_by):
            return cache.get(cache_key)
        return []

    def sync_user_conversations(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> bool:
        """Sync user conversations from Pwaninet."""
        vasto_user_id = self._get_vasto_user_id(user)
        if not vasto_user_id:
            self._log_sync(user, 'conversations', 'error', error='No Vasto user ID', triggered_by=triggered_by)
            return False

        data = self._fetch_from_pwaninet('conversations', vasto_user_id)
        if not data:
            self._log_sync(user, 'conversations', 'error', error='Failed to fetch from Pwaninet', triggered_by=triggered_by)
            return False

        conversations = data.get('conversations', [])
        cache_expires = timezone.now() + timedelta(seconds=settings.CACHE_CONVERSATIONS_TTL)

        try:
            UserConversationCache.objects.filter(user=user).delete()
            for conv in conversations:
                UserConversationCache.objects.create(
                    user=user,
                    vasto_conversation_id=str(conv.get('id', '')),
                    cached_data=conv,
                    cache_expires_at=cache_expires,
                    unread_count=conv.get('unread_count', 0),
                    last_message_id=str(conv.get('last_message_id', '')),
                )

            cache.set(f"conversations:{user.id}", conversations, timeout=settings.CACHE_CONVERSATIONS_TTL)
            self._log_sync(user, 'conversations', 'success', items_synced=len(conversations), triggered_by=triggered_by)
            return True
        except Exception as e:
            logger.error(f"Failed to cache conversations for {user.username}: {e}")
            self._log_sync(user, 'conversations', 'error', error=str(e), triggered_by=triggered_by)
            return False

    def get_user_conversations(self, user, force_refresh: bool = False, triggered_by: str = 'user') -> Optional[list]:
        """Get user conversations from cache or sync if needed."""
        cache_key = f"conversations:{user.id}"
        cached = cache.get(cache_key)
        if cached and not force_refresh:
            return cached

        try:
            convs = UserConversationCache.objects.filter(
                user=user,
                cache_expires_at__gt=timezone.now()
            )
            if convs and not force_refresh:
                return [c.cached_data for c in convs]
        except Exception:
            pass

        if self.sync_user_conversations(user, force_refresh=True, triggered_by=triggered_by):
            return cache.get(cache_key)
        return []

    def sync_all_user_data(self, user, triggered_by: str = 'scheduled') -> dict:
        """Sync all data types for a user."""
        results = {}

        results['profile'] = self.sync_user_profile(user, triggered_by=triggered_by)
        results['documents'] = self.sync_user_documents(user, triggered_by=triggered_by)
        results['institution'] = self.sync_user_institution(user, triggered_by=triggered_by)
        results['courses'] = self.sync_user_courses(user, triggered_by=triggered_by)
        results['programmes'] = self.sync_user_programmes(user, triggered_by=triggered_by)
        results['groups'] = self.sync_user_groups(user, triggered_by=triggered_by)
        results['notifications'] = self.sync_user_notifications(user, triggered_by=triggered_by)
        results['conversations'] = self.sync_user_conversations(user, triggered_by=triggered_by)

        self._log_sync(user, 'full', 'success' if all(results.values()) else 'partial',
                      items_synced=sum(1 for v in results.values() if v), triggered_by=triggered_by)

        return results

    def cleanup_expired_cache(self):
        """Remove expired cache entries from database."""
        now = timezone.now()
        deleted = {}

        for model in [UserProfileCache, UserDocumentCache, UserInstitutionCache,
                     UserChatCache, UserCourseCache, UserProgrammeCache, UserGroupCache,
                     UserNotificationCache, UserConversationCache]:
            count, _ = model.objects.filter(cache_expires_at__lt=now).delete()
            deleted[model.__name__] = count

        logger.info(f"Cache cleanup completed: {deleted}")
        return deleted

    def cleanup_old_sync_logs(self, days: int = 30):
        """Remove old sync logs."""
        cutoff = timezone.now() - timedelta(days=days)
        count, _ = SyncLog.objects.filter(created_at__lt=cutoff).delete()
        logger.info(f"Deleted {count} old sync logs")
        return count
