"""
This type stub file was generated by pyright.
"""

from typing import Optional
from rest_framework.routers import BaseRouter, DefaultRouter, SimpleRouter
from rest_framework.viewsets import GenericViewSet


class NestedRegistryItem:
    def __init__(self, router: BaseRouter, parent_prefix: str, parent_item: NestedRegistryItem = ..., parent_viewset: type[GenericViewSet] = ...) -> None:
        ...

    def register(self, prefix: str, viewset: type[GenericViewSet], basename: Optional[str], parents_query_lookups: list[str]) -> NestedRegistryItem:
        ...

    def get_prefix(self, current_prefix: str, parents_query_lookups: list[str]) -> str:
        ...

    def get_parent_prefix(self, parents_query_lookups: list[str]) -> str:
        ...


class NestedRouterMixin:
    def register(self, prefix: str, viewset: type[GenericViewSet], basename: Optional[str] = ..., base_name: Optional[str] = ...) -> NestedRegistryItem:
        ...


class ExtendedRouterMixin(NestedRouterMixin):
    ...


class ExtendedSimpleRouter(ExtendedRouterMixin, SimpleRouter):
    ...


class ExtendedDefaultRouter(ExtendedRouterMixin, DefaultRouter):
    ...
