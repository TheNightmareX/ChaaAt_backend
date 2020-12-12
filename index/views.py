from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ParseError, AuthenticationFailed
from rest_framework.decorators import action

from django.contrib import auth
from django.db.models.query import QuerySet
from django.dispatch import Signal
from django.db.models.signals import post_save

from drfutils.mixins import AsyncMixin, AsyncCreateModelMixin, AsyncDestroyModelMixin, UpdateManagerMixin
from . import serializers as s
from . import models as m
from drfutils.decorators import require_params

import asyncio as aio
from asgiref.sync import sync_to_async as asy


class UserAPIViewSet(GenericViewSet,
                     CreateModelMixin,
                     RetrieveModelMixin):
    queryset = m.User.objects.all()
    serializer_class = s.UserSerializer
    lookup_field = 'username'

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return super().get_permissions()


class AuthAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request):
        return Response(self.serialized_user)

    @require_params(essentials=['username', 'password'])
    def post(self, request: Request, params):
        if not (user := auth.authenticate(username=params['username'], password=params['password'])):
            raise AuthenticationFailed()
        auth.login(request, user)
        return Response(self.serialized_user, status=HTTP_201_CREATED)

    def delete(self, request: Request):
        auth.logout(request)
        return Response(status=HTTP_204_NO_CONTENT)

    @property
    def serialized_user(self):
        return s.UserSerializer(self.request.user).data


class FriendRelationAPIViewSet(AsyncMixin, GenericViewSet, UpdateManagerMixin,
                               ListModelMixin,
                               AsyncCreateModelMixin, CreateModelMixin,
                               AsyncDestroyModelMixin, DestroyModelMixin):
    queryset = m.FriendRelation.objects.all()
    serializer_class = s.FriendRelationSerializer

    def get_queryset(self):
        super().get_queryset()
        """Filter out the related ones.
        """
        user = self.request.user
        qs = m.FriendRelation.objects.filter(
            m.m.Q(source_user=user) | m.m.Q(target_user=user)
        )
        return qs.order_by('id')

    async def perform_create(self, serializer: s.s.Serializer):
        """Commit the updation.
        """
        await super().perform_create(serializer)
        instance: m.FriendRelation = serializer.instance
        for field in ['source_user', 'target_user']:
            username = str(await asy(getattr)(instance, field))
            update = ('save', serializer.data)
            self.commit_update(username, update)

    async def perform_destroy(self, instance):
        """Commit the updation
        """
        pk = instance.pk
        await super().perform_destroy(instance)
        for field in ['source_user', 'target_user']:
            username = str(await asy(getattr)(instance, field))
            update = ('delete', pk)
            self.commit_update(username, update)

    @action(['get', 'delete'], detail=False)
    async def updates(self, request: Request):
        data = None
        username = str(request.user)
        method: str = request.method
        if method == 'GET':
            # get updates
            data = []
            if updates := self.pop_cached_updates(username):
                # cache exists: return the cached updates
                data.extend(updates)
            else:
                # cache not exists: return the next update
                if update := await self.wait_update(username):
                    data.append(update)
        else:
            # clear the cached updates
            self.pop_cached_updates(username)
        return Response(data)


class ChatroomAPIViewSet(GenericViewSet,
                         CreateModelMixin,
                         ListModelMixin):
    queryset = m.Chatroom.objects.all()
    serializer_class = s.ChatroomSerializer

    @require_params(optionals={'member_contains': None})
    def get_queryset(self, params):
        member_contains = params['member_contains']
        if member_contains:
            try:
                return m.Chatroom.objects.filter(members=member_contains)
            except ValueError as e:
                raise ParseError(e)
        else:
            return super().get_queryset()


class MessageAPIViewSet(AsyncMixin, GenericViewSet,
                        CreateModelMixin,
                        ListModelMixin):
    queryset = m.Message.objects.all()
    serializer_class = s.MessageSerializer

    @require_params(optionals={'from': 1})
    def get_queryset(self, params):
        """Only show the messages that are related to the current user.
        """
        chatrooms = m.Chatroom.objects.filter(members=self.request.user)
        return m.Message.objects.filter(id__gte=params['from'], chatroom__in=chatrooms).order_by('id')

    async def list(self, request, *args, **kwargs):
        """Wait at most 30 seconds for the queryset's existence.
        """
        qs: QuerySet = self.get_queryset()
        if not await asy(qs.exists)():
            future = aio.Future()
            signal: Signal = post_save

            def receiver(sender, **kwargs):
                if qs.exists():
                    future.set_result(None)
                    signal.disconnect(receiver)
            signal.connect(receiver, sender=qs.model)

            try:
                await aio.wait_for(future, 30)
            except aio.TimeoutError:
                pass
        return await asy(super().list)(request, *args, **kwargs)
