"""Utility functions."""

import functools
import weakref


def weak_method_proxy(method):
    """Return a weak reference proxy to a method.

    Should be used when passing methods as callbacks to Maya.
    """
    instance = method.__self__
    unbound_method = getattr(instance.__class__, method.__name__)

    return functools.partial(unbound_method, weakref.proxy(instance))


def ensure_iterable(objects, accepted_types=(list, tuple, set), cast_as=list):
    """
    Convenience function to return given objects if they are an accepted
    iterable type, otherwise cast to the given type.

    Args:
        objects (object): Objects to ensure is iterable.
        accepted_types (tuple(type)): Tuple of accepted iterable types to compare to.
        cast_as (type): Type to cast to and return.

    Returns:
        (list/object): Objects as an iterable.
    """
    # If no objects were given, ensure we return an empty desired iterable.
    if not objects:
        return cast_as()

    if isinstance(objects, accepted_types):
        return objects

    if issubclass(cast_as, list):
        return [objects]

    elif issubclass(cast_as, tuple):
        return (objects,)

    elif issubclass(cast_as, set):
        return {objects}

    else:
        # Try to unpack
        try:
            return cast_as(*objects)

        # Unpack failed, try to use directly
        except TypeError:
            try:
                return cast_as(objects)

            except Exception:
                raise TypeError('Cannot cast to unhandled type "{}".'.format(cast_as))
