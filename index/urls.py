from django.urls import include, path
from django.urls.conf import re_path
from rest_framework_extensions.routers import ExtendedDefaultRouter

from . import consumers, views

router = ExtendedDefaultRouter()

router.register('users', views.UserViewSet,
                basename=None)

router.register('chatrooms', views.ChatroomViewSet,
                basename=None)

router.register('friendships', views.FriendshipViewSet,
                basename=None)
router.register('friendship-groups', views.FriendshipGroupViewSet,
                basename=None)
router.register('friendship-requests', views.FriendshipRequestViewSet,
                basename=None)


router.register('memberships', views.ChatroomMembershipViewSet,
                basename=None)
router.register('membership-groups', views.ChatroomMembershipGroupViewSet,
                basename=None)
router.register('membership-requests', views.ChatroomMembershipRequestViewSet,
                basename=None)

router.register('messages', views.MessageViewSet,
                basename=None)

urlpatterns = [
    path('drf-auth/', include('rest_framework.urls')),
    path('auth/', views.AuthAPIView.as_view()),
]
urlpatterns += router.urls


ws_urlpatterns = [
    re_path(r'ws/updates/$', consumers.UpdateConsumer.as_asgi()),
]
