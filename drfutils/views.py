import asyncio as aio
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar, Union

from asgiref.sync import sync_to_async
from django.db import models
from rest_framework import serializers, status
from rest_framework.exceptions import ParseError
from rest_framework.mixins import (CreateModelMixin, DestroyModelMixin,
                                   UpdateModelMixin)
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.utils.serializer_helpers import ReturnDict
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

_T = TypeVar('_T')


def require_params(essentials: list[str] = [], optionals: dict[str, Any] = {}) -> Callable[[Callable[..., _T]], Callable[..., _T]]:
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


class ActionPermissionsMixin(GenericViewSet):
    """Determine permissions based on the action.

    Example:

            class MyAPIViewSet(ModelViewSet, ActionPermissionsMixin):
                permission_classes = [IsAuthenticated]
                action_permission_classes = {
                    'create': (False, [AllowAny]),
                    'update': (True, [AllowAny]),
                    'partial_update': 'update',
                }
            # retrieve, ...: [IsAuthenticated()]
            # create: [AllowAny()]
            # update, partial_update: [IsAuthenticated(), AllowAny()]
    """
    # {<action>: (<preserve_original_permissions>, <action_permissions>) | <another_action>}
    action_permission_classes: (
        dict[str, Union[str, tuple[bool, list[type[BasePermission]]]]]
    ) = {}

    def get_permissions(self):  # type: ignore
        return self.get_action_permissions(self.action)

    def get_action_permissions(self, action: str) -> list[BasePermission]:
        permissions: list[BasePermission] = []

        action_permission_classes_item = self.action_permission_classes.get(
            action, (True, [])
        )

        if isinstance(action_permission_classes_item, tuple):
            preserve, permission_classes = action_permission_classes_item
            if preserve:
                permissions += super().get_permissions()  # type: ignore
            permissions += [permission_class()
                            for permission_class in permission_classes]
            return permissions
        else:
            return self.get_action_permissions(action_permission_classes_item)


class ActionSerializerKwargsSerializerMixin(GenericViewSet):
    action_serializer_kwargs: (
        dict[tuple[str, ...], dict[str, Any]]
    ) = {}

    def get_serializer(self, *args: Any, **kwargs: Any) -> serializers.BaseSerializer[Any]:
        for actions, kwds in self.action_serializer_kwargs.items():
            if self.action in actions:
                kwargs.update(kwds)
                break
        return super().get_serializer(*args, **kwargs)  # type: ignore


class AsyncMixin(GenericViewSet):
    """Provides async view compatible support for DRF Views and ViewSets.

    This must be the first inherited class.

        class MyViewSet(AsyncMixin, GenericViewSet):
            pass
    """
    @classmethod
    def as_view(cls, *args: Any, **initkwargs: Any):  # type: ignore
        """Make Django process the view as an async view.
        """
        view = super().as_view(*args, **initkwargs)

        async def async_view(*args: Any, **kwargs: Any) -> Awaitable[Response]:
            # wait for the `dispatch` method
            return await view(*args, **kwargs)  # type: ignore
        return async_view

    async def dispatch(self, request: Request, *args: Any, **kwargs: Any):
        """Add async support.
        """
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(
            request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers

        try:
            await sync_to_async(self.initial)(request, *args, **kwargs)

            if request.method and request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(),
                                  self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed

            # accept both async and sync handlers
            # built-in handlers are sync handlers
            if not aio.iscoroutinefunction(handler):
                handler = sync_to_async(handler)
            response = await handler(request, *args, **kwargs)  # type: ignore

        except Exception as exc:
            response = self.handle_exception(exc)

        self.response = self.finalize_response(
            request, response, *args, **kwargs)  # type: ignore
        return self.response


class AsyncBulkCreateModelMixin(CreateModelMixin):
    """Make `create()` and `perform_create()` overridable and provide bulk creation operation support.

    Without inheriting this class, the event loop can't be used in these two methods when override them.

        class MyViewSet(AsyncMixin, GenericViewSet, AsyncCreateModelMixin):
            pass
    """
    async def create(self, request: Request, *args: Any, **kwargs: Any):  # type: ignore
        many = True if type(request.data) == list else False
        serializer: serializers.BaseSerializer[Any]
        serializer = self.get_serializer(  # type: ignore
            data=request.data, many=many)
        await sync_to_async(serializer.is_valid)(raise_exception=True)
        await self.perform_create(serializer)
        data: ReturnDict = await sync_to_async(lambda: serializer.data)()
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    async def perform_create(  # type: ignore
        self, serializer: serializers.BaseSerializer[Any]
    ):
        await sync_to_async(serializer.save)()


class AsyncUpdateModelMixin(UpdateModelMixin):
    """Make `create()` and `perform_create()` overridable.

    Without inheriting this class, the event loop can't be used in these two methods when override them.

        class MyViewSet(AsyncMixin, GenericViewSet, AsyncUpdateModelMixin):
            pass
    """
    async def update(self, request: Request, *args: Any, **kwargs: Any):  # type: ignore
        partial = kwargs.pop('partial', False)
        instance: models.Model = await sync_to_async(
            self.get_object  # type: ignore
        )()
        serializer: serializers.BaseSerializer[Any]
        serializer = self.get_serializer(instance, data=request.data,  # type: ignore
                                         partial=partial)
        await sync_to_async(
            serializer.is_valid
        )(raise_exception=True)
        await self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}  # type: ignore

        return Response(
            await sync_to_async(lambda: serializer.data)())

    async def perform_update(  # type: ignore
            self, serializer: serializers.BaseSerializer[Any]):
        await sync_to_async(serializer.save)()

    async def partial_update(self, request: Request, *args: Any, **kwargs: Any):  # type: ignore
        kwargs['partial'] = True
        return await self.update(request, *args, **kwargs)


class AsyncDestroyModelMixin(DestroyModelMixin):
    """Make `destroy()` and `perform_destroy()` overridable.

    Without inheriting this class, the event loop can't be used in these two methods when override them.

        class MyViewSet(AsyncMixin, GenericViewSet, AsyncDestroyModelMixin):
            pass
    """
    async def destroy(self, request: Request, *args: Any, **kwargs: Any):  # type: ignore
        instance: models.Model
        instance = await sync_to_async(self.get_object)()  # type: ignore
        await self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    async def perform_destroy(self, instance: models.Model):  # type: ignore
        await sync_to_async(instance.delete)()
