from typing import Any

from django.contrib import auth
from django.db.models import Q
from django.db.models.query_utils import Q
from django.utils import timezone
from drfutils.views import require_params
from rest_flex_fields.views import FlexFieldsMixin
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.filters import SearchFilter
from rest_framework.mixins import (CreateModelMixin, DestroyModelMixin,
                                   ListModelMixin, RetrieveModelMixin,
                                   UpdateModelMixin)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from index import policies

from . import models, serializers


class AuthAPIView(APIView):
    permission_classes = [policies.AuthAccessPolicy]

    def get(self, request: Request):
        return Response(self.auth_info)

    @require_params(essentials=['username', 'password'])
    def post(self, request: Request, params: dict[str, Any]):
        if not (user := auth.authenticate(username=params['username'], password=params['password'])):
            raise AuthenticationFailed()
        auth.login(request, user)
        return Response(self.auth_info, status=status.HTTP_201_CREATED)

    def delete(self, request: Request):
        auth.logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @property
    def auth_info(self):
        if isinstance(self.request.user, models.User):
            return serializers.UserSerializer(instance=self.request.user, fields=['pk', 'username']).data
        else:
            return None


class UserViewSet(FlexFieldsMixin, GenericViewSet,
                  ListModelMixin,
                  CreateModelMixin,
                  RetrieveModelMixin,
                  UpdateModelMixin):
    queryset = models.User.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = [policies.UserAccessPolicy]

    filter_backends = [SearchFilter]
    search_fields = ['username']


class ChatroomViewSet(FlexFieldsMixin, ModelViewSet):
    queryset = models.Chatroom.objects.all()
    serializer_class = serializers.ChatroomSerializer
    permission_classes = [policies.ChatroomAccessPolicy]

    filterset_fields = ['friendship_exclusive']

    permit_list_expands = ['creator']


class ChatroomMembershipGroupViewSet(FlexFieldsMixin, ModelViewSet):
    queryset = models.ChatroomMembershipGroup.objects.all()
    serializer_class = serializers.ChatroomMembershipGroupSerializer
    permission_classes = [policies.GenericGroupAccessPolicy]

    def get_queryset(self):
        return models.ChatroomMembershipGroup.objects.filter(
            user=self.request.user
        )


class ChatroomMembershipViewSet(FlexFieldsMixin, GenericViewSet,
                                ListModelMixin,
                                RetrieveModelMixin,
                                UpdateModelMixin,
                                DestroyModelMixin):
    queryset = models.ChatroomMembership.objects.all()
    serializer_class = serializers.ChatroomMembershipSerializer
    permission_classes = [policies.ChatroomMembershipAccessPolicy]

    filterset_fields = ['user', 'chatroom', 'groups']

    permit_list_expands = ['user', 'chatroom', 'chatroom.creator']

    def get_queryset(self):
        return models.ChatroomMembership.objects.filter(
            chatroom__memberships__user=self.request.user,
        )

    @action(methods=['POST'], detail=True)
    def promote(self, request: Request, *args: Any, **kwargs: Any):
        instance: models.ChatroomMembership = self.get_object()
        instance.is_manager = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['POST'], detail=True)
    def demote(self, request: Request, *args: Any, **kwargs: Any):
        instance: models.ChatroomMembership = self.get_object()
        instance.is_manager = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['POST'], detail=True)
    def read(self, request: Request, *args: Any, **kwargs: Any):
        instance: models.ChatroomMembership = self.get_object()
        instance.last_read = timezone.now()
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatroomMembershipRequestViewSet(FlexFieldsMixin, GenericViewSet,
                                       ListModelMixin,
                                       CreateModelMixin,
                                       RetrieveModelMixin,
                                       DestroyModelMixin):
    queryset = models.ChatroomMembershipRequest.objects.all()
    serializer_class = serializers.ChatroomMembershipRequestSerializer
    permission_classes = [policies.ChatroomMembershipRequestAccessPolicy]

    filterset_fields = ['state', 'user', 'chatroom']

    permit_list_expands = ['user', 'chatroom', 'chatroom.creator']

    def get_queryset(self):
        own_manager_memberships = models.ChatroomMembership.objects.filter(
            user=self.request.user, is_manager=True)
        return models.ChatroomMembershipRequest.objects.filter(
            Q(chatroom__friendship_exclusive=False)
            & (Q(user=self.request.user) | Q(chatroom__memberships__in=own_manager_memberships))
        )

    def create_membership(self, membership_request: models.ChatroomMembershipRequest):
        return models.ChatroomMembership.objects.create(
            user=membership_request.user,
            chatroom=membership_request.chatroom,
        )

    @action(methods=['POST'], detail=True)
    def accept(self, request: Request, *args: Any, **kwargs: Any):
        instance: models.ChatroomMembershipRequest = self.get_object()
        instance.state = 'A'
        self.create_membership(instance)
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['POST'], detail=True)
    def reject(self, request: Request, *args: Any, **kwargs: Any):
        instance: models.ChatroomMembershipRequest = self.get_object()
        instance.state = 'R'
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FriendshipGroupViewSet(FlexFieldsMixin, ModelViewSet):
    queryset = models.FriendshipGroup.objects.all()
    serializer_class = serializers.FriendshipGroupSerializer
    permission_classes = [policies.GenericGroupAccessPolicy]

    def get_queryset(self):
        return models.FriendshipGroup.objects.filter(
            user=self.request.user
        )


class FriendshipViewSet(FlexFieldsMixin, GenericViewSet,
                        ListModelMixin,
                        RetrieveModelMixin,
                        UpdateModelMixin,
                        DestroyModelMixin):
    queryset = models.Friendship.objects.all()
    serializer_class = serializers.FriendshipSerializer
    permission_classes = [policies.FriendshipAccessPolicy]

    filterset_fields = ['groups']

    permit_list_expands = ['target', 'chatroom', 'chatroom.creator']

    def get_queryset(self):
        return models.Friendship.objects.filter(
            user=self.request.user
        )


class FriendshipRequestViewSet(FlexFieldsMixin, GenericViewSet,
                               ListModelMixin,
                               CreateModelMixin,
                               RetrieveModelMixin,
                               DestroyModelMixin):
    queryset = models.FriendshipRequest.objects.all()
    serializer_class = serializers.FriendshipRequestSerializer
    permission_classes = [policies.FriendshipRequestAccessPolicy]

    filterset_fields = ['state']

    permit_list_expands = ['user', 'target']

    def get_queryset(self):
        return models.FriendshipRequest.objects.filter(
            Q(user=self.request.user)
            | Q(target=self.request.user)
        )

    def create_friendship(self, instance: models.FriendshipRequest):
        """Create the requested friendship.
        """
        return models.Friendship.objects.create(
            user=instance.user,
            target=instance.target,
        )

    @action(methods=['POST'], detail=True)
    def accept(self, request: Request, *args: Any, **kwargs: Any):
        instance: models.FriendshipRequest = self.get_object()
        self.create_friendship(instance)
        instance.state = 'A'
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['POST'], detail=True)
    def reject(self, request: Request, *args: Any, **kwargs: Any):
        instance: models.FriendshipRequest = self.get_object()
        instance.state = 'R'
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageViewSet(FlexFieldsMixin, GenericViewSet,
                     ListModelMixin,
                     CreateModelMixin,
                     RetrieveModelMixin):
    queryset = models.Message.objects.all()
    serializer_class = serializers.MessageSerializer
    permission_classes = [policies.MessageAccessPolicy]

    filterset_fields = ['sender_membership']

    def get_queryset(self):
        return models.Message.objects.filter(
            chatroom__memberships__user=self.request.user
        )
