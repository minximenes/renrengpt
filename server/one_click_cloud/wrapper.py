from flask import request
from functools import wraps
# inner import
from one_click_cloud.auth import varifyToken


def varifyRequestTokenWrapper(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return PermissionError("Authorization is missing.")

        varified = varifyToken(token)
        if varified.get("expired"):
            raise PermissionError("Authorization is expired.")

        kwargs["varified"] = varified
        return func(*args, **kwargs)

    return wrapper
