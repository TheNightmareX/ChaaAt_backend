from typing import Iterable, TypeVar, Union

from django.db.models import Model
from django.db.models.manager import Manager
from django.db.models.query import QuerySet

_M = TypeVar('_M', bound=Model)


class RelatedManager(Manager[_M]):
    """Provide type for foreign managers and m2m managers.

    It exists because Django's built-in RelatedManager is not exposed.
    """
    related_val: tuple[int, ...]
    def add(self, *objs: Union[_M, int], bulk: bool = ...) -> None: ...
    def remove(self, *objs: Union[_M, int], bulk: bool = ...) -> None: ...
    def set(self, objs: Union[QuerySet[_M], Iterable[Union[_M, int]]],
            *, bulk: bool = ..., clear: bool = ...) -> None: ...

    def clear(self) -> None: ...
