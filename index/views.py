from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ParseError, AuthenticationFailed

from django.contrib import auth

from .asyncwrap import AsyncViewWrap
from . import serializers as s
from . import models as m

import asyncio
from asgiref.sync import sync_to_async as asy


class UserAPIViewSet(GenericViewSet, CreateModelMixin, RetrieveModelMixin):
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

    def post(self, request: Request):
        try:
            username: str = request.data['username']
            password: str = request.data['password']
        except KeyError as key:
            raise ParseError(f'`{key}` is required.')

        if not (user := auth.authenticate(username=username, password=password)):
            raise AuthenticationFailed()
        auth.login(request, user)
        return Response(self.serialized_user, status=HTTP_201_CREATED)

    def delete(self, request: Request):
        auth.logout(request)
        return Response(status=HTTP_204_NO_CONTENT)

    @property
    def serialized_user(self):
        return s.UserSerializer(self.request.user).data


class FriendAPIViewSet(GenericViewSet, ListModelMixin, CreateModelMixin, DestroyModelMixin):
    queryset = m.FriendRelation.objects.all()
    serializer_class = s.FriendRelationSerializer

    def get_queryset(self):
        user = self.request.user
        return m.FriendRelation.objects.filter(m.m.Q(source_user=user) | m.m.Q(target_user=user)).order_by('id')


class ChatroomAPIViewSet(GenericViewSet, CreateModelMixin, ListModelMixin):
    queryset = m.Chatroom.objects.all()
    serializer_class = s.ChatroomSerializer

    def get_queryset(self):
        member_contains = self.request.query_params.get('member_contains')
        if member_contains:
            try:
                return m.Chatroom.objects.filter(members=member_contains)
            except ValueError as e:
                raise ParseError(e)
        else:
            return super().get_queryset()


class MessageAPIViewSet(AsyncViewWrap, GenericViewSet, CreateModelMixin, ListModelMixin):
    queryset = m.Message.objects.all()
    serializer_class = s.MessageSerializer

    def get_queryset(self):
        """Only show the messages that are related to the current user.
        """
        id_from = int(self.request.query_params.get('from', 1))
        chatrooms = m.Chatroom.objects.filter(members=self.request.user)
        return m.Message.objects.filter(id__gte=id_from, chatroom__in=chatrooms).order_by('id')

    async def list(self, request, *args, **kwargs):
        """If the requested queryset does not exist, wait at most 10s for the queryset.

        I once tried to realize it by awaiting a `Future` object but 
        failed because the async views are processed in different 
        event loops and it seems that setting the `Future` object's 
        result in another event loop is impossible.

        I am still looking for a better way...
        """
        qs = self.get_queryset()
        max_wait = 10
        waited = 0
        interval = 0.1
        while not await asy(qs.exists)() and waited < max_wait:
            await asyncio.sleep(interval)
            waited += interval

        return await asy(super().list)(request, *args, **kwargs)
