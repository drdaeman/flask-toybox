from __future__ import absolute_import

from .exceptions import PreconditionRequired, NotModified
from flask import abort
import base64
import hashlib
import types

METHODS_REQUIRE_IF_MATCH = set(["PUT", "DELETE", "PATCH"])

def _raw_object_serialize(obj):
    """
    Unsafe serializer of raw object's content using `repr`.

    This intended to be used internally by `ETagger` class, when no serializer
    is provided.
    """
    d = obj.as_dict(check_permissions=False)
    for k in sorted(d.keys()):
        yield k
        yield ":"
        yield repr(d[k])

class ETagger(object):
    def __init__(self, req, serializer):
        self.etag = None
        self.serializer = serializer
        self.req = req

    def set_etag(self, etag):
        if self.req.method in METHODS_REQUIRE_IF_MATCH:
            # The problem with weak tags, is that If-Match MUST use strong
            # comparsion. This was fixed in HTTPbis, for further details
            # see http://trac.tools.ietf.org/wg/httpbis/trac/ticket/116
            if not self.req.if_match:
                raise PreconditionRequired
            elif etag not in self.req.if_match:
                abort(412)
        elif self.req.method == "GET":
            self.etag = etag
            if self.req.if_none_match and etag in self.req.if_none_match:
                raise NotModified

    def set_raw(self, data, prefix="raw"):
        etag = hashlib.sha1()
        if type(data) is types.GeneratorType:
            for element in data: etag.update(element)
        else:
            etag.update(data)
        etag.update(data)
        digest = base64.b64encode(etag.digest()).rstrip("=")
        self.set_etag("{0}-{1}".format(prefix, digest))

    def set_object(self, obj):
        if self.serializer is not None:
            pname = getattr(self.serializer, "name",
                            self.serializer.__class__.__name__.lower())
            serialize = self.serializer.serialize
        else:
            pname = "none"
            serialize = _raw_object_serialize
        self.set_raw(serialize(obj), pname)