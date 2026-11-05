"""DRF API views for cached user data."""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from identity.services.data_sync import DataSyncService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get cached user profile."""
    force_refresh = request.GET.get('refresh', '').lower() == 'true'
    service = DataSyncService()
    data = service.get_user_profile(request.user, force_refresh=force_refresh, triggered_by='user')

    if data is None:
        return Response({'error': 'Profile not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_documents(request):
    """Get cached user documents."""
    force_refresh = request.GET.get('refresh', '').lower() == 'true'
    service = DataSyncService()
    data = service.get_user_documents(request.user, force_refresh=force_refresh, triggered_by='user')

    if data is None:
        return Response({'error': 'Documents not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({'documents': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_institution(request):
    """Get cached user institution."""
    force_refresh = request.GET.get('refresh', '').lower() == 'true'
    service = DataSyncService()
    data = service.get_user_institution(request.user, force_refresh=force_refresh, triggered_by='user')

    if data is None:
        return Response({'error': 'Institution not available'}, status=status.HTTP_404_NOT_FOUND)

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_courses(request):
    """Get cached user courses."""
    force_refresh = request.GET.get('refresh', '').lower() == 'true'
    service = DataSyncService()
    data = service.get_user_courses(request.user, force_refresh=force_refresh, triggered_by='user')

    if data is None:
        return Response({'error': 'Courses not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({'courses': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_groups(request):
    """Get cached user groups."""
    force_refresh = request.GET.get('refresh', '').lower() == 'true'
    service = DataSyncService()
    data = service.get_user_groups(request.user, force_refresh=force_refresh, triggered_by='user')

    if data is None:
        return Response({'error': 'Groups not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({'groups': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_notifications(request):
    """Get cached user notifications."""
    force_refresh = request.GET.get('refresh', '').lower() == 'true'
    service = DataSyncService()
    data = service.get_user_notifications(request.user, force_refresh=force_refresh, triggered_by='user')

    if data is None:
        return Response({'error': 'Notifications not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({'notifications': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_conversations(request):
    """Get cached user conversations."""
    force_refresh = request.GET.get('refresh', '').lower() == 'true'
    service = DataSyncService()
    data = service.get_user_conversations(request.user, force_refresh=force_refresh, triggered_by='user')

    if data is None:
        return Response({'error': 'Conversations not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({'conversations': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_user_data(request):
    """Manually trigger sync for current user."""
    sync_types = request.data.get('types', None)
    if sync_types is None:
        sync_types = ['profile', 'documents', 'institution', 'courses', 'groups', 'notifications', 'conversations']
    elif not isinstance(sync_types, list):
        return Response({'error': 'types must be a list'}, status=status.HTTP_400_BAD_REQUEST)

    service = DataSyncService()
    results = service.sync_all_user_data(request.user, triggered_by='user')

    return Response({
        'status': 'success',
        'results': results,
        'message': 'Sync completed'
    })
