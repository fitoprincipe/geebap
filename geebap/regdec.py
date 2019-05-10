# -*- coding: utf-8 -*-
""" Registry Decorator """

import functools

__all__ = ('register', 'register_all')


def register(holder):
    """ Make a registry of the decorated Class in the given holder

    :Usage:

    .. code:: python

        from regdec import register
        from scores import Score

        registry = {}

        @register(registry)
        class NewScore(Score):
            def __init__(**kwargs):
                pass

    :param holder: dict that will hold the classes
    :type holder: dict
    """
    # @functools.wraps(holder)
    def wrap(cls):
        name = cls.__name__
        holder[name] = cls
        return cls
    return wrap


def register_all(holder):
    """ Make a registry of the decorated Class in the given holder to use in
    module's __all__ variable

    :Usage:

    .. code:: python

        from regdec import register
        from scores import Score

        __all__ = []

        @register_all(__all__)
        class NewScore(Score):
            def __init__(**kwargs):
                pass

    :param holder: list that will hold the classe's names
    :type holder: list
    """
    # @functools.wraps(holder)
    def wrap(cls):
        name = cls.__name__
        holder.append(name)
        return cls
    return wrap
