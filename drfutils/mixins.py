import asyncio as aio
from typing import Any, Awaitable, Callable

from asgiref.sync import sync_to_async
from django.db import models as m
from rest_framework import serializers as s
from rest_framework import status
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin
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


class AsyncCreateModelMixin(CreateModelMixin):
    """Make `create()` and `perform_create()` overridable.

    Without inheriting this class, the event loop can't be used in these two methods when override them.

        class MyViewSet(AsyncMixin, GenericViewSet, AsyncCreateModelMixin):
            pass
    """
    async def create(self, request: Request, *args: Any, **kwargs: Any):
        serializer: s.Serializer[m.Model]
        serializer = self.get_serializer(data=request.data)
        await sync_to_async(serializer.is_valid)(
            raise_exception=True)  # MODIFIED HERE
        await self.perform_create(serializer)  # MODIFIED HERE
        data: ReturnDict
        data = await sync_to_async(lambda: serializer.data)()  # MODIFIED HERE
        headers: dict[str, str]
        headers = self.get_success_headers(data)  # MODIFIED HERE
        return Response(data,  # MODIFIED HERE
                        status=status.HTTP_201_CREATED,
                        headers=headers)

    async def perform_create(self, serializer: s.Serializer[m.Model]):
        await sync_to_async(serializer.save)()


class AsyncDestroyModelMixin(DestroyModelMixin):
    """Make `destroy()` and `perform_destroy()` overridable.

    Without inheriting this class, the event loop can't be used in these two methods when override them.

        class MyViewSet(AsyncMixin, GenericViewSet, AsyncDestroyModelMixin):
            pass
    """
    async def destroy(self, request: Request, *args: Any, **kwargs: Any):
        instance: m.Model
        instance = await sync_to_async(self.get_object)()  # MODIFIED HERE
        await self.perform_destroy(instance)  # MODIFIED HERE
        return Response(status=status.HTTP_204_NO_CONTENT)

    async def perform_destroy(self, instance: m.Model):
        await sync_to_async(instance.delete)()  # MODIFIED HERE
