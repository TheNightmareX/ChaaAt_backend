from rest_framework.request import Request
from rest_framework.exceptions import ParseError, ValidationError

from functools import wraps


def require_params(essentials: list[str] = [], optionals: dict[str] = {}):
    """Get the params from both query params and data and pass the params into the 
    keyword argument `param`.
    """
    def decorator(fn):
        @wraps(fn)
        def wrap(self, *args, **kwargs):
            request: Request = self.request
            query, data = request.query_params, request.data
            query = query if type(query) == dict else query.dict()
            data = data if type(data) == dict else data.dict()
            all = {}
            all.update(query)
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


def validation(fn):
    """Provide a more convenient way to validate.

    It will convert the AssertionError into ValidationError and return the value 
    automatically if there's no error.
    """
    @wraps(fn)
    def wrap(self, value):
        try:
            fn(self, value)
            return value
        except AssertionError as e:
            raise ValidationError(e)
    return wrap
