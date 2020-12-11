from typing import Callable

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

from .mixins import AsyncMixin, AsyncCreateModelMixin
from . import serializers as s
from . import models as m
from .decorators import require_params

import asyncio
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


class FriendRelationAPIViewSet(AsyncMixin, GenericViewSet,
                               ListModelMixin,
                               AsyncCreateModelMixin, CreateModelMixin,
                               DestroyModelMixin):
    queryset = m.FriendRelation.objects.all()
    serializer_class = s.FriendRelationSerializer

    unsynced_updations_mapping: dict[str, list[int]] = {}
    updation_callbacks: list[Callable[[m.FriendRelation], None]] = []

    @property
    def unsynced_updations(self):
        """Returns the unsynced updations of the current user. (referenced by address)
        """
        key = self.request.session.session_key
        self.unsynced_updations_mapping.setdefault(key, [])
        return self.unsynced_updations_mapping[key]

    def get_queryset(self):
        super().get_queryset()
        """Filter out the related ones. If the action is 'updation', extraly filter out the
        updated ones.
        """
        user = self.request.user
        qs = m.FriendRelation.objects.filter(
            m.m.Q(source_user=user) | m.m.Q(target_user=user)
        )
        if self.action == 'updations':
            qs = qs.filter(id__in=self.unsynced_updations)
        return qs.order_by('id')

    def is_related_instance(self, instance: m.FriendRelation) -> bool:
        """Whether the `FriendRelation` is related to the current user.
        """
        user = self.request.user
        return instance.source_user == user or instance.target_user == user

    async def perform_create(self, serializer: s.s.Serializer):
        """Call the callbacks when a updation happens.
        """
        await super().perform_create(serializer)
        instance = serializer.instance
        self.unsynced_updations.append(instance.pk)
        [callback(instance) for callback in self.updation_callbacks]
        

    def wait_for_updation(self) -> m.FriendRelation:
        """Returns a `Future` which will be finished when a updation happens.
        """
        future = asyncio.Future()

        def callback(instance: m.FriendRelation):
            if self.is_related_instance(instance):
                future.set_result(instance)
                self.updation_callbacks.remove(callback)
        self.updation_callbacks.append(callback)

        return future

    @action(['get', 'delete'], detail=False)
    async def updations(self, request: Request):
        data = None
        if self.request.method == 'GET':
            unsynced_relations = self.unsynced_updations

            if not unsynced_relations:
                try:
                    await self.wait_for_updation(30)
                except asyncio.TimeoutError:
                    pass
            qs = self.get_queryset()
            serializer: s.s.Serializer = self.get_serializer(qs, many=True)
            data = await asy(lambda: serializer.data)()
        self.unsynced_updations.clear()
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
            future = asyncio.Future()
            signal: Signal = post_save

            def receiver(sender, **kwargs):
                if qs.exists():
                    future.set_result(None)
                    signal.disconnect(receiver)
            signal.connect(receiver, sender=qs.model)

            try:
                await asyncio.wait_for(future, 30)
            except asyncio.TimeoutError:
                pass
        return await asy(super().list)(request, *args, **kwargs)
