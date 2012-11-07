"""
When we think about HTTP API, one point is in what format(s) we exchange data.
I believe hardcoding is not a viable option and formats have to be configurable
and extensible.

In ToyBox, there are two concepts for this, called *serializers* and
*deserializers*. The names are hopefully self-describing.
"""

import json
import collections
import decimal

class ExtendedJSONEncoder(json.JSONEncoder):
    """
    Extended JSON encoder, that may come useful when implementing web APIs.

    Features for top-level objects:

    - If object has `to_json` attribute, it is used to represent object.
      Return string representation from there, and it'll get straight to the
      resulting JSON document.

    - If object is a namedtuple (or anything similar that's a tuple and
      has `_fields` attribute), it is represented as an JSON object (dict).

    Features for any objects, including deeply contained ones:

    - If object has `as_dict` or `as_list` methods, they're used to represent
      it as JSON object or list, respectively.

    - If object has `isoformat` method (for example, a `datetime` does) it's
      represented as JSON string.

    - `decimal.Decimal` values are represented as JSON strings (not numbers).

    - Otherwise, standard `json.JSONEncoder` rules apply.

    Usage example:

    >>> json.dumps(collections.namedtuple("whatever", "spam eggs")(
    ...     datetime.datetime(2012, 1, 1, 0, 0, 0), decimal.Decimal("42.42")),
    ...     cls=ExtendedJSONEncoder)
    '{"spam": "2012-01-01T00:00:00", "eggs": "42,42"}'

    """
    def encode(self, obj):
        if hasattr(obj, "to_json"):
            return obj.to_json()
        if isinstance(obj, tuple) and hasattr(obj, "_fields"):
            obj = collections.OrderedDict((k, v) for k, v in zip(obj._fields, obj))
        return super(ExtendedJSONEncoder, self).encode(obj)

    def default(self, obj):
        if hasattr(obj, "as_dict"):
            return obj.as_dict()
        elif hasattr(obj, "as_list"):
            return obj.as_list()
        elif hasattr(obj, "isoformat"):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return str(obj)
        return super(ExtendedJSONEncoder, self).default(obj) # pragma: no cover

class JSON(object):
    """
    JSON serializer and deserializer.
    """
    mime_types = [
        "application/json",          # RFC4627, rest are compatibility
        "application/x-javascript",
        "text/javascript",
        "text/x-javascript",
        "text/x-json",
    ]

    @staticmethod
    def serialize(data):
        return json.dumps(data, cls=ExtendedJSONEncoder)

    @staticmethod
    def deserialize(data):
        return json.loads(data) # pragma: no cover
