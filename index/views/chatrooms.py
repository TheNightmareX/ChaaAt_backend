from drfutils.decorators import require_params
from rest_framework.exceptions import ParseError
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.viewsets import GenericViewSet

from .. import models as m
from .. import serializers as s


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
