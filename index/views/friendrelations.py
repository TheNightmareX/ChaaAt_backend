from asgiref.sync import sync_to_async as asy
from drfutils.mixins import (AsyncCreateModelMixin, AsyncDestroyModelMixin,
                             AsyncMixin)
from rest_framework.mixins import (CreateModelMixin, DestroyModelMixin,
                                   ListModelMixin)
from rest_framework.utils.serializer_helpers import ReturnDict
from rest_framework.viewsets import GenericViewSet

from .. import models as m
from .. import serializers as s
from .updates import UpdateManager


class FriendRelationAPIViewSet(AsyncMixin, GenericViewSet,
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

    async def perform_create(self, serializer: s.FriendRelationSerializer):
        """Commit the updation.
        """
        await super().perform_create(serializer)
        instance = serializer.instance
        for field in ['source_user', 'target_user']:
            username = str(await asy(getattr)(instance, field))
            update: ReturnDict = await asy(lambda: serializer.data)()
            UpdateManager(
                username, label='friend_relation.create').commit(update)

    async def perform_destroy(self, instance: m.FriendRelation):
        """Commit the updation
        """
        pk = instance.pk
        await super().perform_destroy(instance)
        for field in ['source_user', 'target_user']:
            username = str(await asy(getattr)(instance, field))
            update = pk
            UpdateManager(
                username, label='friend_relation.destroy').commit(update)
