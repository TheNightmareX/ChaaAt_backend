import asyncio as aio
from typing import Any, Awaitable, Callable

from asgiref.sync import sync_to_async
from django.db import models as m
from rest_framework import serializers as s
from rest_framework import status
from rest_framework.mixins import (CreateModelMixin, DestroyModelMixin,
                                   UpdateModelMixin)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.utils.serializer_helpers import ReturnDict


class AsyncMixin:
    """Provides async view compatible support for DRF Views and ViewSets.

    This must be the first inherited class.

        class MyViewSet(AsyncMixin, GenericViewSet):
            pass
    """
    @classmethod
    def as_view(cls, *args: Any, **initkwargs: Any):
        """Make Django process the view as an async view.
        """
        view: Callable[[Request], Awaitable[Response]]
        view = super().as_view(*args, **initkwargs)

        async def async_view(*args: Any, **kwargs: Any) -> Awaitable[Response]:
            # wait for the `dispatch` method
            return await view(*args, **kwargs)
        return async_view

    async def dispatch(self, request, *args, **kwargs):
        """Add async support.
        """
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers

        try:
            await sync_to_async(self.initial)(
                request, *args, **kwargs)  # MODIFIED HERE

            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(),
                                  self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed

            # accept both async and sync handlers
            # built-in handlers are sync handlers
            if not aio.iscoroutinefunction(handler):  # MODIFIED HERE
                handler = sync_to_async(handler)  # MODIFIED HERE
            response = await handler(request, *args, **kwargs)  # MODIFIED HERE

        except Exception as exc:
            response = self.handle_exception(exc)

        self.response = self.finalize_response(
            request, response, *args, **kwargs)
        return self.response


class AsyncBulkCreateModelMixin(CreateModelMixin):
    """Make `create()` and `perform_create()` overridable and provide bulk creation operation support.

    Without inheriting this class, the event loop can't be used in these two methods when override them.

        class MyViewSet(AsyncMixin, GenericViewSet, AsyncCreateModelMixin):
            pass
    """
    async def create(self, request: Request, *args: Any, **kwargs: Any):
        many = True if type(request.data) == list else False
        serializer: s.BaseSerializer[Any]
        serializer = self.get_serializer(data=request.data, many=many)
        await sync_to_async(serializer.is_valid)(raise_exception=True)
        await self.perform_create(serializer)
        data: ReturnDict = await sync_to_async(lambda: serializer.data)()
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    async def perform_create(self, serializer: s.BaseSerializer[Any]):
        await sync_to_async(serializer.save)()


class AsyncUpdateModelMixin(UpdateModelMixin):
    """Make `create()` and `perform_create()` overridable.

    Without inheriting this class, the event loop can't be used in these two methods when override them.

        class MyViewSet(AsyncMixin, GenericViewSet, AsyncUpdateModelMixin):
            pass
    """
    async def update(self, request: Request, *args: Any, **kwargs: Any):
        partial = kwargs.pop('partial', False)
        instance: m.Model = await sync_to_async(self.get_object)()
        serializer: s.BaseSerializer[Any]
        serializer = self.get_serializer(instance, data=request.data,
                                         partial=partial)
        await sync_to_async(serializer.is_valid)(raise_exception=True)
        await self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(await sync_to_async(lambda: serializer.data)())

    async def perform_update(self, serializer: s.BaseSerializer[Any]):
        await sync_to_async(serializer.save)()

    async def partial_update(self, request: Request, *args: Any, **kwargs: Any):
        kwargs['partial'] = True
        return await self.update(request, *args, **kwargs)


class AsyncDestroyModelMixin(DestroyModelMixin):
    """Make `destroy()` and `perform_destroy()` overridable.

    Without inheriting this class, the event loop can't be used in these two methods when override them.

        class MyViewSet(AsyncMixin, GenericViewSet, AsyncDestroyModelMixin):
            pass
    """
    async def destroy(self, request: Request, *args: Any, **kwargs: Any):
        instance: m.Model
        instance = await sync_to_async(self.get_object)()
        await self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    async def perform_destroy(self, instance: m.Model):
        await sync_to_async(instance.delete)()
