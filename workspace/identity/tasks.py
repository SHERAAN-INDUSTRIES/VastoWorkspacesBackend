"""Celery tasks for data synchronization."""
import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from identity.services.data_sync import DataSyncService

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_user_data_task(self, user_id: int, sync_types: list = None, triggered_by: str = 'user'):
    """Sync data for a specific user."""
    try:
        user = User.objects.get(id=user_id)
        service = DataSyncService()

        if sync_types is None:
            sync_types = ['profile', 'documents', 'institution', 'courses', 'programmes', 'groups', 'notifications', 'conversations']

        results = {}
        for sync_type in sync_types:
            try:
                if sync_type == 'profile':
                    results[sync_type] = service.sync_user_profile(user, triggered_by=triggered_by)
                elif sync_type == 'documents':
                    results[sync_type] = service.sync_user_documents(user, triggered_by=triggered_by)
                elif sync_type == 'institution':
                    results[sync_type] = service.sync_user_institution(user, triggered_by=triggered_by)
                elif sync_type == 'courses':
                    results[sync_type] = service.sync_user_courses(user, triggered_by=triggered_by)
                elif sync_type == 'programmes':
                    results[sync_type] = service.sync_user_programmes(user, triggered_by=triggered_by)
                elif sync_type == 'groups':
                    results[sync_type] = service.sync_user_groups(user, triggered_by=triggered_by)
                elif sync_type == 'notifications':
                    results[sync_type] = service.sync_user_notifications(user, triggered_by=triggered_by)
                elif sync_type == 'conversations':
                    results[sync_type] = service.sync_user_conversations(user, triggered_by=triggered_by)
            except Exception as e:
                logger.error(f"Error syncing {sync_type} for user {user_id}: {e}")
                results[sync_type] = False

        return results
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'error': 'User not found'}
    except Exception as exc:
        logger.error(f"Task failed for user {user_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def daily_full_sync_all_users():
    """Daily full sync for all active users."""
    logger.info("Starting daily full sync for all users")
    service = DataSyncService()
    users = User.objects.filter(is_active=True)
    total = users.count()
    synced = 0
    failed = 0

    for user in users:
        try:
            results = service.sync_all_user_data(user, triggered_by='scheduled')
            if all(results.values()):
                synced += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Error syncing user {user.id}: {e}")
            failed += 1

    logger.info(f"Daily sync completed: {synced} synced, {failed} failed out of {total} users")
    return {'synced': synced, 'failed': failed, 'total': total}


@shared_task
def hourly_incremental_sync():
    """Hourly incremental sync for active users (last 24 hours)."""
    logger.info("Starting hourly incremental sync")
    service = DataSyncService()
    cutoff = timezone.now() - timedelta(hours=24)

    # Get users who have been active recently
    active_users = User.objects.filter(
        is_active=True,
        last_login__gte=cutoff
    )

    total = active_users.count()
    synced = 0
    failed = 0

    for user in active_users:
        try:
            # Only sync frequently changing data for incremental sync
            results = service.sync_all_user_data(user, triggered_by='scheduled')
            if all(results.values()):
                synced += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Error syncing user {user.id}: {e}")
            failed += 1

    logger.info(f"Hourly sync completed: {synced} synced, {failed} failed out of {total} users")
    return {'synced': synced, 'failed': failed, 'total': total}


@shared_task
def sync_notifications_active_users():
    """Sync notifications for recently active users."""
    logger.info("Starting notifications sync for active users")
    service = DataSyncService()
    cutoff = timezone.now() - timedelta(minutes=30)

    # Get users who have been active in last 30 minutes
    active_users = User.objects.filter(
        is_active=True,
        last_login__gte=cutoff
    )

    synced = 0
    failed = 0

    for user in active_users:
        try:
            if service.sync_user_notifications(user, triggered_by='scheduled'):
                synced += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Error syncing notifications for user {user.id}: {e}")
            failed += 1

    logger.info(f"Notifications sync completed: {synced} synced, {failed} failed")
    return {'synced': synced, 'failed': failed}


@shared_task
def sync_conversations_active_users():
    """Sync conversations for recently active users."""
    logger.info("Starting conversations sync for active users")
    service = DataSyncService()
    cutoff = timezone.now() - timedelta(minutes=30)

    active_users = User.objects.filter(
        is_active=True,
        last_login__gte=cutoff
    )

    synced = 0
    failed = 0

    for user in active_users:
        try:
            if service.sync_user_conversations(user, triggered_by='scheduled'):
                synced += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Error syncing conversations for user {user.id}: {e}")
            failed += 1

    logger.info(f"Conversations sync completed: {synced} synced, {failed} failed")
    return {'synced': synced, 'failed': failed}


@shared_task
def sync_groups_all_users():
    """Sync groups for all users (less frequent)."""
    logger.info("Starting groups sync for all users")
    service = DataSyncService()
    users = User.objects.filter(is_active=True)

    synced = 0
    failed = 0

    for user in users:
        try:
            if service.sync_user_groups(user, triggered_by='scheduled'):
                synced += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Error syncing groups for user {user.id}: {e}")
            failed += 1

    logger.info(f"Groups sync completed: {synced} synced, {failed} failed")
    return {'synced': synced, 'failed': failed}


@shared_task
def cleanup_expired_cache():
    """Clean up expired cache entries."""
    logger.info("Starting cache cleanup")
    service = DataSyncService()
    result = service.cleanup_expired_cache()
    logger.info(f"Cache cleanup completed: {result}")
    return result


@shared_task
def cleanup_old_sync_logs():
    """Clean up old sync logs."""
    logger.info("Starting sync log cleanup")
    service = DataSyncService()
    count = service.cleanup_old_sync_logs(days=30)
    logger.info(f"Deleted {count} old sync logs")
    return {'deleted': count}
