"""
TBD.
"""
from __future__ import absolute_import

from flask import Response, request, current_app, g
from flask.views import MethodView
import werkzeug.exceptions
from . import exceptions, etags
from .utils import is_printable
from functools import wraps

def append_vary(response, vary_on):
    """
    Given a `Response` objects and a header name, checks whenever a header is
    listed in response's `Vary` header(s), and adds one if missing.

    If there are multiple `Vary` headers already, another one is added.
    If there's only single `Vary` header, name is appended to the end.

    Note, the header name comparsion is case insensitive.
    """
    if type(vary_on) in (list, tuple, set, frozenset):
        for header in vary_on:
            append_vary(response, header)
        return

    vary = response.headers.getlist("Vary")
    current_set = set(
        ((name.strip().lower() for name in value.split(",")) for value in vary)
    )
    if vary_on.lower() not in current_set:
        if len(vary) == 1:
            response.headers.set("Vary", vary[0] + ", " + vary_on)
        else:
            response.headers.add("Vary", vary_on)

class NegotiatingMethodView(MethodView):
    """
    A `MethodView`-derived class that negotiates request and response
    content types.

    Two things happen in this class:

    1. If there's a request body, flask's `request` object gets a `decoded_data`
       attribute, that contains Python objects ready for API consumption.

       If request body can't be handled due to unknown or missing `Content-Type`
       header, an `UnsupportedMediaType` exception is raised.

       If there's no request body, the `decoded_data` attribute will be set
       to `None`. If you want to know whenever there was a request body that
       deserialized to `None` or wasn't any, take a look at `request.data`.

    2. In verb-handling methods you should return raw python objects.
       They'll get automatically serialized to a negotiated Content-Type.

       If no content-type could be negotiated due to unacceptable `Accept`
       request header, an `NotAcceptable` exception is raised.
       This negotiation happens *before* the request is handled.

    Example::

        class EchoView(NegotiatingMethodView):
            def get(self):
                # Echoes back a list of GET query param pairs.
                return request.args.items()

            def post(self):
                # Echoes back a received body.
                return request.decoded_data

    To override default (de)serializers you may define two class properties:

    - `SERIALIZERS` - an *ordered* dictionary of serializers, in order of
      preference. Keys are strings of MIME types, values are serializer objects,
      implementing `serialize` method. See the `serialization` package for
      further details.

    - `DESERIALIZERS` - an iterable (preferably, a set) of deserializer classes.

    """
    def negotiate_serializer(self, *args, **kwargs):
        """
        Decide on which serializer will be used to output data.
        Returns a tuple, with first element being MIME type string and
        second being the serializer object to use.

        Raises `NotAcceptable` if no acceptable serializer found, or
        `InternalServerError` if no serializers are defined.
        """
        serializers = getattr(self, "SERIALIZERS",
                              current_app.config["TOYBOX_SERIALIZERS"])

        if len(serializers) > 0:
            mime_type = request.accept_mimetypes.best_match(serializers.keys())
            if mime_type is None:
                raise werkzeug.exceptions.NotAcceptable()
            return mime_type, serializers[mime_type]
        else:
            raise werkzeug.exceptions.InternalServerError()

    def dispatch_request(self, *args, **kwargs):
        if request.method.lower() == "POST":
            method_override = request.headers.get("X-HTTP-Method-Override", None)
            if method_override is not None:
                request.method = method_override

        mime_type, serializer = self.negotiate_serializer(*args, **kwargs)

        # Deserialize the incoming request data (if any)
        deserializers = getattr(self, "DESERIALIZERS",
                                current_app.config["TOYBOX_DESERIALIZERS"])

        decoded_data = None
        has_data = request.data is not None and len(request.data) > 0
        if len(deserializers) > 0 and has_data:
            acceptable = False
            for deserializer in deserializers:
                if request.mimetype in deserializer.mime_types:
                    decoded_data = deserializer.deserialize(request.data)
                    acceptable = True
                    break
            if not acceptable:
                raise werkzeug.exceptions.UnsupportedMediaType()
        else:
            decoded_data = None

        # TODO: Document hydration/dehydration process.
        request.dehydrated_decoded_data = decoded_data
        if hasattr(self, "hydrate"):
            decoded_data = self.hydrate(decoded_data)
        request.decoded_data = decoded_data

        # Provide g.etag_object for ETags
        g.etagger = etagger = etags.ETagger(request, serializer)

        # Call parent.
        result = super(NegotiatingMethodView, self)\
                 .dispatch_request(*args, **kwargs)

        # Handle view's result (response)
        if isinstance(result, Response):
            response = result
        else:
            if type(result) is tuple:
                result, status, headers = result
            else:
                status = None
                headers = None

            if hasattr(self, "dehydrate"):
                result = self.dehydrate(result)

            response = Response(serializer.serialize(result),
                                status, headers, mimetype=mime_type)
            response.serialized_with = serializer

        append_vary(response, ["Accept", "Accept-Encoding"])
        if etagger.etag is not None:
            response.set_etag(etagger.etag)
        return response

class BaseModelView(NegotiatingMethodView):
    """
    A `NegotiatingMethodView`-based class, that simplifies working with
    database models or alike objects. This view is intended to be generic
    and read-only. Use `ModelView` if you need write support.

    This class contains pseudo-abstract method `fetch_object` that you
    must implement in derived classes.
    """

    # Can't use @abstractmethod here due to a metaclass conflict, sorry.
    def fetch_object(self, *args, **kwargs):
        """
        Implement this method in your class.

        Return a (non-dehydrated) object, that matches the request.
        If requested object does not exist, raise `NotFound` exception.
        """
        # TODO: Document object interface (get_columns, check_permissions, etc.)
        raise werkzeug.exceptions.NotImplemented( # pragma: no cover
            "<p>This resource is not implemented on server.</p>")

    def get_object(self, *args, **kwargs):
        """
        Returns an object, the same `fetch_object` returns.
        However, this cached object in `cached_object` property, so database
        (or other model data source) is not queried twice.

        Use this instead of `fetch_object` in view's code.

        Beware, for now object is currently cached independently from
        function's arguments, so calling this again with another arguments will
        lead to errors. So, don't.
        """
        if not hasattr(self, "cached_object") or self.cached_object is None:
            self.cached_object = self.fetch_object(*args, **kwargs)
        return self.cached_object

    def get(self, *args, **kwargs):
        obj = self.get_object(*args, **kwargs)
        headers = {}

        if hasattr(obj, "check_permissions"):
            access = obj.check_permissions()
            if len(access) > 0 and access != {"system"}:
                headers["X-Access-Classes"] = ", ".join(sorted(access))

        return obj, 200, headers

class ModelView(BaseModelView):
    """
    An class on top of `BaseModelView` that provides write support
    for single model instances.
    """

    def get_columns(self, *args, **kwargs):
        return self.get_object(*args, **kwargs).get_columns()

    # TODO: Implement `put` method for object creation and updates.
    # TODO: Implement `delete` method for object deletion.

    def patch(self, *args, **kwargs):
        obj = self.get_object(**kwargs)

        if hasattr(obj, "check_permissions"):
            access = obj.check_permissions()
            columns = {c.name: c.permissions.get("writeable", set())
                       for c in self.get_columns(only_db_columns=True)}
        else:
            access = frozenset(["system"])
            columns = {c.name: frozenset(["system"])
                       for c in self.get_columns(only_db_columns=True)}

        r = {}
        for k, v in request.decoded_data.items():
            name = '"{0}"'.format(k) if is_printable(k) else repr(k)

            if k not in columns:
                error = "<p>No such attribute: {0}</p>".format(name)
                raise exceptions.UnprocessableEntity(error)
            if len(columns.get(k, set()) & access) > 0:
                r[k] = v #, list(columns.get(k, set()) & access)
            else:
                error = "<p>Attribute {0} is not writeable.</p>".format(name)
                raise exceptions.UnprocessableEntity(error)

        for k, v in r.items():
            setattr(obj, k, v)
        if hasattr(self, "save_object"):
            self.save_object(obj)

        return Response(status=204)
