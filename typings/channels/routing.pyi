"""
This type stub file was generated by pyright.
"""

"""
This type stub file was generated by pyright.
"""




from typing import Any


def get_default_application() -> Any:
    """
    Gets the default application, set in the ASGI_APPLICATION setting.
    """
    ...


DEPRECATION_MSG = """
Using ProtocolTypeRouter without an explicit "http" key is deprecated.
Given that you have not passed the "http" you likely should use Django's
get_asgi_application():

    from django.core.asgi import get_asgi_application

    application = ProtocolTypeRouter(
        "http": get_asgi_application()
        # Other protocols here.
    )
"""


class ProtocolTypeRouter:
    """
    Takes a mapping of protocol type names to other Application instances,
    and dispatches to the right one based on protocol name (or raises an error)
    """

    def __init__(self, application_mapping: dict[str, Any]) -> None:
        ...

    async def __call__(self, scope: Any, receive: Any, send: Any) -> Any:
        ...


def route_pattern_match(route: Any, path: Any) -> Any:
    """
    Backport of RegexPattern.match for Django versions before 2.0. Returns
    the remaining path and positional and keyword arguments matched.
    """
    ...


class URLRouter:
    """
    Routes to different applications/consumers based on the URL path.

    Works with anything that has a ``path`` key, but intended for WebSocket
    and HTTP. Uses Django's django.conf.urls objects for resolution -
    url() or path().
    """
    _path_routing: Any = ...

    def __init__(self, routes: list[Any]) -> None:
        ...

    async def __call__(self, scope: Any, receive: Any, send: Any) -> Any:
        ...


class ChannelNameRouter:
    """
    Maps to different applications based on a "channel" key in the scope
    (intended for the Channels worker mode)
    """

    def __init__(self, application_mapping: Any) -> None:
        ...

    async def __call__(self, scope: Any, receive: Any, send: Any) -> Any:
        ...
