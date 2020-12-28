import asyncio as aio
from typing import Any

from drfutils.mixins import AsyncMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class UpdateManager:
    __waiters_mapping: dict[Any, aio.Future] = {}
    __cache_pools_mapping: dict[Any, list[Any]] = {}

    def __init__(self, key: Any, label: str = None):
        self.key = key
        self.label = label

    @staticmethod
    def from_user(request: Request, label: str = None):
        return UpdateManager(str(request.user), label)

    def commit(self, update: Any):
        """Send or cache the update.
        """
        update = [self.label, update]
        if self.key in self.__waiters_mapping:
            # waiting, send update
            self.__waiters_mapping[self.key].set_result(update)
        else:
            # not waiting, cache update
            self.__cache_pools_mapping.setdefault(self.key, [])
            self.__cache_pools_mapping[self.key].append(update)

    async def next(self, timeout: int = 30) -> Any or None:
        """Return the next update or None if it timeout.
        """
        waiters = self.__waiters_mapping

        # An overlap means that another call occurs before
        # the previous call with the same key is completed.
        future = waiters.get(self.key, aio.Future())  # prevent overlaps
        waiters[self.key] = future

        update = None
        try:
            update = await aio.wait_for(future, timeout)
        except aio.TimeoutError:
            pass
        finally:
            # If the request is canceled, any statements outside the
            # `finally` statement will be killed and never executed.
            if self.key in waiters:  # prevent overlaps
                del waiters[self.key]
            # Put the `return` statement inside the `finally` statement
            # because it will block forever when the request is canceled
            # if the `return` statement is outside.
            return update

    def pop_caches(self):
        """Return and clear the cached updates.
        """
        updates = self.__cache_pools_mapping.get(self.key, [])
        self.__cache_pools_mapping[self.key] = []
        return updates


class UpdateAPIView(AsyncMixin, APIView):

    async def get(self, request: Request):
        update_manager = UpdateManager.from_user(request)
        data = []

        if updates := update_manager.pop_caches():
            # cache exists: return the cached updates
            data.extend(updates)
        else:
            # cache not exists: return the next update
            if update := await update_manager.next():
                data.append(update)

        return Response(data)

    def delete(self, request: Request):
        UpdateManager.from_user(request).pop_caches()
        return Response()
