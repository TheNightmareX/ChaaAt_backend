"""
This type stub file was generated by pyright.
"""

from typing import Any

from django.db.models import QuerySet
from django.db.models.query import QuerySet
from rest_framework.request import Request
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import GenericViewSet


class DetailSerializerMixin(GenericViewSet):
    """
    Add custom serializer for detail view
    """
    serializer_detail_class: type[BaseSerializer[Any]] = ...
    queryset_detail: QuerySet[Any] = ...

    def get_serializer_class(self) -> BaseSerializer[Any]:
        ...

    def get_queryset(self, *args: Any, **kwargs: Any) -> QuerySet[Any]:
        ...


class PaginateByMaxMixin(GenericViewSet):
    def get_page_size(self, request: Request) -> int:
        ...


class NestedViewSetMixin(GenericViewSet):
    def get_queryset(self) -> QuerySet[Any]:
        ...

    def filter_queryset_by_parents_lookups(self, queryset: QuerySet[Any]) -> QuerySet[Any]:
        ...

    def get_parents_query_dict(self) -> dict[str, str]:
        ...
