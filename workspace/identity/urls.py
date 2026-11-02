from django.urls import path

from identity import views

urlpatterns = [
    path('vasto/start/', views.vasto_start, name='vasto-start'),
    path('vasto/callback/', views.vasto_callback, name='vasto-callback'),
    path('me/', views.me, name='auth-me'),
    path('logout/', views.logout_view, name='auth-logout'),
]
