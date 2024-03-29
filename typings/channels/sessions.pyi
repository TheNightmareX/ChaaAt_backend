"""
This type stub file was generated by pyright.
"""

from typing import Any


class CookieMiddleware:
    """
    Extracts cookies from HTTP or WebSocket-style scopes and adds them as a
    scope["cookies"] entry with the same format as Django's request.COOKIES.
    """

    def __init__(self, inner: Any) -> Any:
        ...

    async def __call__(self, scope: Any, receive: Any, send: Any) -> Any:
        ...

    @classmethod
    def set_cookie(cls, message: Any, key: Any, value: Any = ..., max_age: Any = ..., expires: Any = ..., path: Any = ..., domain: Any = ..., secure: Any = ..., httponly: Any = ...) -> Any:
        """
        Sets a cookie in the passed HTTP response message.

        ``expires`` can be:
        - a string in the correct format,
        - a naive ``datetime.datetime`` object in UTC,
        - an aware ``datetime.datetime`` object in any time zone.
        If it is a ``datetime.datetime`` object then ``max_age`` will be calculated.
        """
        ...

    @classmethod
    def delete_cookie(cls, message: Any, key: Any, path: Any = ..., domain: Any = ...) -> Any:
        """
        Deletes a cookie in a response.
        """
        ...


class InstanceSessionWrapper:
    """
    Populates the session in application instance scope, and wraps send to save
    the session.
    """
    save_message_types: Any = ...
    cookie_response_message_types: Any = ...

    def __init__(self, scope: Any, send: Any) -> None:
        ...

    async def resolve_session(self) -> Any:
        ...

    async def send(self, message: Any) -> Any:
        """
        Overridden send that also does session saves/cookies.
        """
        ...

    def save_session(self) -> Any:
        """
        Saves the current session.
        """
        ...


class SessionMiddleware:
    """
    Class that adds Django sessions (from HTTP cookies) to the
    scope. Works with HTTP or WebSocket protocol types (or anything that
    provides a "headers" entry in the scope).

    Requires the CookieMiddleware to be higher up in the stack.
    """

    def __init__(self, inner: Any) -> None:
        ...

    async def __call__(self, scope: Any, receive: Any, send: Any) -> Any:
        """
        Instantiate a session wrapper for this scope, resolve the session and
        call the inner application.
        """
        ...


def SessionMiddlewareStack(inner: Any) -> Any:
    ...
