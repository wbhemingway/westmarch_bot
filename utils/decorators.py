from functools import wraps


def with_lock(f):
    """A decorator to acquire and release the async lock on an object."""

    @wraps(f)
    async def wrapper(self, *args, **kwargs):
        async with self.lock:
            return await f(self, *args, **kwargs)

    return wrapper
