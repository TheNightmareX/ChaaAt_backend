from asgiref.sync import sync_to_async
import asyncio


class AsyncViewWrap:
    """Provides async view compatible support for DRF.

    This must be the first inherited class.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convert the sync only methods which have not been overwritten into async methods
        for name in ['initial',
                     'list', 'create', 'retrieve', 'update', 'destroy']:
            method = getattr(self, name, None)
            if not asyncio.iscoroutinefunction(method):
                setattr(self, name, sync_to_async(method))

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
            await self.initial(request, *args, **kwargs)

            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(),
                                  self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed

            # built-in handlers return responses directly
            response = handler(request, *args, **kwargs)
            if asyncio.iscoroutine(response):
                response = await response

        except Exception as exc:
            response = self.handle_exception(exc)

        self.response = self.finalize_response(
            request, response, *args, **kwargs)
        return self.response
