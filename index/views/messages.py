from asgiref.sync import sync_to_async as asy
from django.db.models.manager import BaseManager
from drfutils.mixins import AsyncCreateModelMixin, AsyncMixin
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.viewsets import GenericViewSet

from .. import models as m
from .. import serializers as s
from .updates import UpdateManager


class MessageAPIViewSet(AsyncMixin, GenericViewSet,
                        AsyncCreateModelMixin, CreateModelMixin,
                        ListModelMixin):
    queryset = m.Message.objects.all()
    serializer_class = s.MessageSerializer

    def get_queryset(self):
        """Only show the messages that are related to the current user.
        """
        chatrooms = m.Chatroom.objects.filter(members=self.request.user)
        return m.Message.objects.filter(chatroom__in=chatrooms).order_by('id')

    async def perform_create(self, serializer: s.MessageSerializer):
        await super().perform_create(serializer)
        instance = serializer.instance
        data = serializer.data
        chatroom: m.Chatroom = instance.chatroom
        members: BaseManager[m.User] = chatroom.members
        usernames: list[str] = await asy(lambda: [str(user) for user in members.all()])()
        [UpdateManager(username, label='message.create').commit(data)
         for username in usernames]
