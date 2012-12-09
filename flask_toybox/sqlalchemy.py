"""
Support for using SQLAlchemy models.

This module features `ModelMixin` class, that you should mix into your models
to ease exposing them with ToyBox.

See `ModelMixin` documentation for details.

Note, if PyYaml is installed, a SafeRepresenter as YAML hashmap is added.
"""

from __future__ import absolute_import

from .compat import OrderedDict
from sqlalchemy.orm import column_property, class_mapper, relationship, ColumnProperty, object_session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.schema import Column
from .views import ModelView, BaseModelView
from .permissions import ModelColumnInfo
from flask import g, request
from werkzeug.exceptions import InternalServerError, NotFound
from werkzeug.datastructures import Range, ContentRange

def column_info(model, name, column):
    return ModelColumnInfo(model, name,
                           db_column=isinstance(column, Column),
                           permissions=getattr(column, "info"))

class SAModelMixin(object):
    """
    SQLALchemy model mixin.

    Mix this class to your SQLAlchemy models (not views), to ease using them
    with `ModelView` classes.
    """

    @classmethod
    def _get_permissions(cls, column, what="readable"):
        permissions = column.permissions
        return permissions.get(what, frozenset(["system"]))

    def get_columns(self, only_db_columns=False):
        columns = [
            column_info(self, prop.key, prop.columns[0])
            for prop in class_mapper(self.__class__).iterate_properties
            if isinstance(prop, ColumnProperty) and len(prop.columns) == 1\
               and not prop.key.startswith("_") and\
               (not only_db_columns or isinstance(prop.columns[0], Column))
        ]
        if not only_db_columns:
            # If there's a mix, "real" DB columns should go first
            columns.sort(key=lambda c: c.db_column, reverse=True)
        return columns

    def check_permissions(self):
        return frozenset(["system"])

    def as_dict(self, check_permissions=True):
        columns = self.get_columns()

        if check_permissions:
            levels = self.check_permissions()
            columns = [c for c in columns
                       if any(l in self.__class__._get_permissions(c)
                              for l in levels)]

        return OrderedDict((c.name, getattr(self, c.name)) for c in columns)

    @staticmethod
    def yaml_safe_representer(dumper, data):
        return dumper.represent_mapping(
            u'tag:yaml.org,2002:map', data.as_dict().items(), flow_style=False)

try:
    from yaml.representer import SafeRepresenter
    SafeRepresenter.add_multi_representer(
        SAModelMixin, SAModelMixin.yaml_safe_representer)
    del SafeRepresenter
except ImportError: # pragma: no cover
    pass

def hasUserMixin(owner_id_field):
    """
    Quite specific helper, that was made to ease working with permissions
    for models referencing Django-like user objects.
    """
    class HasUserMixin(object):
        def check_permissions(self, user=None):
            if user is None and hasattr(g, "user"):
                user = g.user

            p = set()
            if user is not None:
                p.add("authenticated")
                if owner_id_field is not None:
                    if user.id == getattr(self, owner_id_field): p.add("owner")
                if getattr(user, "is_superuser", False): p.add("admin")
                if getattr(user, "is_staff", False): p.add("staff")
            else:
                p.add("anonymous")
            return p
    return HasUserMixin

class SAModelViewBase(object):
    def __init__(self, *args, **kwargs):
        if not hasattr(self, "model") or len(args) > 0:
            raise InternalServerError("<p>Server entity misconfiguration.</p>")
        return super(SAModelViewBase, self).__init__(*args, **kwargs)

    def query_class(self, model):
        """
        Returns an object, that's API-compatible with `sqlalchemy.orm.query.Query`.

        Default implementation is a function that uses Flask-SQLAlchemy's provided
        `model.query`. If you have a class, say `session.query`, implement this as
        a property.
        """
        if model != self.model:
            raise ValueError("Invalid model passed to SAModelViewBase.query_class")
        return self.model.query

class SAModelView(SAModelViewBase, ModelView):
    def get_query(self, *args, **kwargs):
        return self.query_class(self.model).filter_by(**kwargs)

    def fetch_object(self, *args, **kwargs):
        try:
            obj = self.get_query(*args, **kwargs).one()
        except NoResultFound:
            raise NotFound()
        if hasattr(g, "etagger"):
            g.etagger.set_object(obj)
        return obj

class SACollectionView(SAModelViewBase, BaseModelView):
    def get_query(self, *args, **kwargs):
        q = self.query_class(self.model)
        if len(kwargs) > 0:
            q = q.filter_by(**kwargs)
        return q

    def fetch_object(self, *args, **kwargs):
        q = self.get_query(*args, **kwargs)
        if hasattr(self, "limit_query"):
            q = self.limit_query(q)
        objs = q.all()
        if hasattr(g, "etagger"):
            g.etagger.set_object(objs)
        return objs

class PaginableByNumber(object):
    """
    Mixin class, adding support for pagination by item number. Append this class
    from the left (i.e. `class Foo(PaginableByNumber, ...)` to hook in.

    This type of pagination is fine if you have reasonably small queries
    where `OFFSET n` clauses work well.

    To paginate, use `Range` header with `items` unit. For example, requesting
    `Range: items=0-10` will result in `.limit(10).offset(0)` being applied
    to parent's `get_query()` result.

    Set `order_by` to `False` if you do ordering by yourself, otherwise query
    will be automatically ordered on primary key(s).
    """
    max_limit = 50
    order_by = None

    def __init__(self, *args, **kwargs):
        super(PaginableByNumber, self).__init__(*args, **kwargs)
        if self.order_by is None:
            order_by = [c for c in class_mapper(self.model).primary_key]
        self._content_range = None

    def limit_query(self, q):
        # q = super(PaginableByNumber, self).limit_query(q)
        order_by = self.order_by
        if order_by is not None and order_by is not False:
            if isinstance(order_by, basestring) or not hasattr(order_by, "__iter__"):
                order_by = (order_by,)
            q = q.order_by(*order_by)

        limit = 50
        r = request.range
        if r is not None:
            if r.units != "items":
                raise RequestedRangeNotSatisfiable("Unacceptable unit: '{0}'".format(r.units))
            if len(r.ranges) > 1:
                raise RequestedRangeNotSatisfiable("Multiple ranges are not supported")
            begin, end = r.ranges[0]
            if begin is None:
                raise RequestedRangeNotSatisfiable("First item offset must be clearly specified")
            limit = end - begin
            if limit < 1:
                raise RequestedRangeNotSatisfiable("Invalid range")
            elif self.max_limit is not None and limit > self.max_limit:
                raise RequestedRangeNotSatisfiable("Won't return more than {0:d} items".format(self.max_limit))
            q = q.offset(begin)
            self._content_range = begin
        # XXX: While we're limiting anyway, according to HTTP spec we return 206 only if there was a Range header.
        q = q.limit(limit)
        return q

    def dehydrate(self, data):
        if self._content_range is not None:
            # Unfortunately, Range.make_content_range does not seem
            # to like units other than bytes, so it goes this way.
            begin = self._content_range
            self._content_range = ContentRange("items", begin, begin + len(data))
        return data

    def handle_response(self, response):
        if self._content_range is not None:
            response.status = "206 Partial Content"
            if isinstance(self._content_range, ContentRange):
                response.headers.set("Content-Range", self._content_range)
        return response
