from typing import Protocol

from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from index import models


class HasUser(Protocol):
    user: models.User


class HasState(Protocol):
    state: str


def as_owner(request: Request, view: GenericViewSet, action: str):
    obj: HasUser = view.get_object()
    return request.user == obj.user


def state_is(request: Request, view: GenericViewSet, action: str, value: str):
    obj: HasState = view.get_object()
    return obj.state == value
