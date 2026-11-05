from django.urls import path

from identity import views, api_views

urlpatterns = [
    # OAuth flow
    path('vasto/start/', views.vasto_start, name='vasto-start'),
    path('vasto/callback/', views.vasto_callback, name='vasto-callback'),
    path('me/', views.me, name='auth-me'),
    path('logout/', views.logout_view, name='auth-logout'),

    # Cached data API endpoints
    path('user/profile/', api_views.user_profile, name='user-profile'),
    path('user/documents/', api_views.user_documents, name='user-documents'),
    path('user/institution/', api_views.user_institution, name='user-institution'),
    path('user/courses/', api_views.user_courses, name='user-courses'),
    path('user/programmes/', api_views.user_programmes, name='user-programmes'),
    path('user/groups/', api_views.user_groups, name='user-groups'),
    path('user/notifications/', api_views.user_notifications, name='user-notifications'),
    path('user/conversations/', api_views.user_conversations, name='user-conversations'),
    path('user/programme-units/', api_views.user_programme_units, name='user-programme-units'),
    path('user/timetable/', api_views.user_timetable, name='user-timetable'),
    path('user/follows/', api_views.user_follows, name='user-follows'),
    path('user/sync/', api_views.sync_user_data, name='user-sync'),
]
