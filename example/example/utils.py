from __future__ import absolute_import
from . import app

def class_route(path, name=None, **kwargs):
    if name is None:
        name = cls.__name__.lower()

    def _class_view_decorator(cls):
        app.add_url_rule(path, view_func=cls.as_view(name), **kwargs)
        return cls

    return _class_view_decorator
