from functools import wraps
from typing import Any, Callable, TypeVar
from django.db.models.base import Model

from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.request import Request
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

T = TypeVar('T')


def require_params(essentials: list[str] = [], optionals: dict[str, Any] = {}) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Get the params from both query params and data and pass the params into the 
    keyword argument `param`.
    """
    def decorator(fn: Callable[..., Any]):
        @wraps(fn)
        def wrap(self: APIView, *args: Any, **kwargs: Any):
            request: Request = self.request
            query, data = request.query_params, request.data
            all = {}
            all.update(query.dict())
            all.update(data)
            params = {}
            try:
                for k in essentials:
                    params[k] = all[k]
            except KeyError as k:
                raise ParseError(f'Param {k} is required.')
            for k in optionals:
                params[k] = all.get(k, optionals[k])
            return fn(self, *args, **kwargs, params=params)
        return wrap
    return decorator


def validation(fn: Callable[..., None]):
    """Provide a more convenient way to validate.

    It will convert the AssertionError into ValidationError and return the value 
    automatically if there's no error.
    """
    @wraps(fn)
    def wrap(self: Serializer[Model], value: T):
        try:
            fn(self, value)
            return value
        except AssertionError as e:
            raise ValidationError(str(e))
    return wrap
