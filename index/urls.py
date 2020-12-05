from rest_framework import urlpatterns
from rest_framework.routers import DefaultRouter
from django.urls import path

from . import views


router = DefaultRouter()
router.register('users', views.UserAPIViewSet)
router.register('friend-relations', views.FriendAPIViewSet)
router.register('chatrooms', views.ChatroomAPIViewSet)
router.register('messages', views.MessageAPIViewSet)

urlpatterns = [
    path('auth/', views.AuthAPIView.as_view()),
]

urlpatterns += router.urls
