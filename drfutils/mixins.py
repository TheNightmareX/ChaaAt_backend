from typing import Any

from rest_framework.response import Response
from rest_framework import status

from asgiref.sync import sync_to_async
import asyncio as aio


class AsyncMixin:
    """Provides async view compatible support for DRF Views and ViewSets.

    This must be the first inherited class.

        class MyViewSet(AsyncMixin, GenericViewSet):
            pass
    """
    @classmethod
    def as_view(cls, *args, **initkwargs):
        """Make Django process the view as an async view.
        """
        view = super().as_view(*args, **initkwargs)

        async def async_view(*args, **kwargs):
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


class AsyncCreateModelMixin:
    """Make `create()` and `perform_create()` overridable.

    Without inheriting this class, the event loop can't be used in these two methods when override them.

    This must be inherited before `CreateModelMixin`.

        class MyViewSet(AsyncMixin, GenericViewSet, AsyncCreateModelMixin, CreateModelMixin):
            pass
    """
    async def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        await sync_to_async(serializer.is_valid)(
            raise_exception=True)  # MODIFIED HERE
        await self.perform_create(serializer)  # MODIFIED HERE
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    async def perform_create(self, serializer):
        await sync_to_async(serializer.save)()


class AsyncDestroyModelMixin:
    """Make `destroy()` and `perform_destroy()` overridable.

    Without inheriting this class, the event loop can't be used in these two methods when override them.

    This must be inherited before `DestroyModelMixin`.

        class MyViewSet(AsyncMixin, GenericViewSet, AsyncDestroyModelMixin, DestroyModelMixin):
            pass
    """
    async def destroy(self, request, *args, **kwargs):
        instance = await sync_to_async(self.get_object)()  # MODIFIED HERE
        await self.perform_destroy(instance)  # MODIFIED HERE
        return Response(status=status.HTTP_204_NO_CONTENT)

    async def perform_destroy(self, instance):
        await sync_to_async(instance.delete)()  # MODIFIED HERE


class UpdateManagerMixin:
    """Provide methods about updates.
    """
    __update_waiters: dict[Any, aio.Future] = {}
    __updates_cache_pool: dict[Any, list[Any]] = {}

    def commit_update(self, key: str, update):
        """Send or cache the update.
        """
        if key in self.__update_waiters:
            # waiting, send update
            self.__update_waiters[key].set_result(update)
            del self.__update_waiters[key]
        else:
            # not waiting, cache update
            self.__updates_cache_pool.setdefault(key, [])
            self.__updates_cache_pool[key].append(update)

    async def wait_update(self, key: str, timeout: int = 30):
        """Return the next update or None if it timeout.
        """
        future = aio.Future()
        self.__update_waiters[key] = future
        update = None
        try:
            update = await aio.wait_for(future, timeout)
        except aio.TimeoutError:
            pass
        return update

    def pop_cached_updates(self, key: str):
        """Return and clear the cached updates.
        """
        updates = self.__updates_cache_pool.get(key, [])
        self.__updates_cache_pool[key] = []
        return updates
