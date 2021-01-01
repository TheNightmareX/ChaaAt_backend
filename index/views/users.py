from rest_framework.filters import SearchFilter
from rest_framework.mixins import (CreateModelMixin, ListModelMixin,
                                   RetrieveModelMixin)
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import GenericViewSet

from .. import models as m
from .. import serializers as s
from ..paginations import SmallPageNumberPagination


class UserAPIViewSet(GenericViewSet,
                     ListModelMixin,
                     CreateModelMixin,
                     RetrieveModelMixin):
    queryset = m.User.objects.all()
    serializer_class = s.UserSerializer
    lookup_field = 'username'
    filter_backends = [SearchFilter]
    search_fields = ['username']
    pagination_class = SmallPageNumberPagination

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return super().get_permissions()
