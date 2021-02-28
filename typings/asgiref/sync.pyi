"""
This type stub file was generated by pyright.
"""

import os
from typing import Any, Awaitable, Callable, TypeVar


_RT = TypeVar('_RT')


class AsyncToSync():
    """
    Utility class which turns an awaitable that only works on the thread with
    the event loop into a synchronous callable that works in a subthread.

    If the call stack contains an async loop, the code runs there.
    Otherwise, the code runs in a new loop in a new thread.

    Either way, this thread then pauses and waits to run any thread_sensitive
    code called from further down the call stack using SyncToAsync, before
    finally exiting once the async task returns.
    """
    launch_map: dict[str, Any] = ...
    executors: Any = ...

    def __init__(self, awaitable: Any, force_new_loop: bool = ...) -> None:
        ...

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...

    def __get__(self, parent: Any, objtype: Any) -> Any:
        """
        Include self for methods
        """
        ...

    async def main_wrap(self, args: list[Any], kwargs: dict[str, Any], call_result: Any, source_thread: Any, exc_info: Any, context: Any) -> Any:
        """
        Wraps the awaitable with something that puts the result into the
        result/exception future.
        """
        ...


class SyncToAsync:
    """
    Utility class which turns a synchronous callable into an awaitable that
    runs in a threadpool. It also sets a threadlocal inside the thread so
    calls to AsyncToSync can escape it.

    If thread_sensitive is passed, the code will run in the same thread as any
    outer code. This is needed for underlying Python code that is not
    threadsafe (for example, code which handles SQLite database connections).

    If the outermost program is async (i.e. SyncToAsync is outermost), then
    this will be a dedicated single sub-thread that all sync code runs in,
    one after the other. If the outermost program is sync (i.e. AsyncToSync is
    outermost), this will just be the main thread. This is achieved by idling
    with a CurrentThreadExecutor while AsyncToSync is blocking its sync parent,
    rather than just blocking.
    """
    if "ASGI_THREADS" in os.environ:
        loop: Any = ...
    launch_map: Any = ...
    threadlocal: Any = ...
    single_thread_executor: Any = ...

    def __init__(self, func: Any, thread_sensitive: Any=...) -> None:
        ...

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...

    def __get__(self, parent: Any, objtype: Any) -> Any:
        """
        Include self for methods
        """
        ...

    def thread_handler(self, loop: Any, source_task: Any, exc_info: Any, func: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Wraps the sync application with exception handling.
        """
        ...

    @staticmethod
    def get_current_task() -> Any:
        """
        Cross-version implementation of asyncio.current_task()

        Returns None if there is no task.
        """
        ...


async_to_sync = AsyncToSync


def sync_to_async(func: Callable[..., _RT]=..., thread_sensitive: bool=...) -> Callable[..., Awaitable[_RT]]:
    ...
