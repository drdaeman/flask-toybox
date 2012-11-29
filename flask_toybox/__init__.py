from __future__ import absolute_import

from .serialization import JSON
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

class ToyBox(object):
    def __init__(self, app):
        self.app = app
        self.init_app(app)

    def init_app(self, app):
        app.config.setdefault("TOYBOX_SERIALIZERS", OrderedDict([
            ("application/json", JSON),
            ("text/json", JSON),
        ]))
        app.config.setdefault("TOYBOX_DESERIALIZERS", set([JSON]))
