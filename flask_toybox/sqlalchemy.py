"""
Support for using SQLAlchemy models.

This module features `ModelMixin` class, that you should mix into your models
to ease exposing them with ToyBox.

See `ModelMixin` documentation for details.

Note, if PyYaml is installed, a SafeRepresenter as YAML hashmap is added.
"""

from __future__ import absolute_import

from collections import OrderedDict
from sqlalchemy.orm import column_property, class_mapper, relationship, ColumnProperty, object_session
from sqlalchemy.schema import Column
from .views import ModelView
from .permissions import ModelColumnInfo
from flask import g
from werkzeug.exceptions import InternalServerError

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
                if user.is_superuser: p.add("admin")
                if user.is_staff: p.add("staff")
                if user.id == getattr(self, owner_id_field): p.add("owner")
            else:
                p.add("anonymous")
            return p
    return HasUserMixin

def saModelView(session):
    """
    Given an SQLAlchemy session object, returns a class that provides some
    possibly useful default implementations for `get_object`.
    """
    class SAModelView(ModelView):
        def __init__(self, *args, **kwargs):
            if not hasattr(self, "model") or len(args) > 0:
                raise InternalServerError("<p>Server entity misconfiguration.</p>")
            return super(SAModelView, self).__init__(*args, **kwargs)

        def fetch_object(self, *args, **kwargs):
            model = self.model
            obj = session.query(model).filter_by(**kwargs).one()
            if hasattr(g, "etagger"):
                g.etagger.set_object(obj)
            return obj

        def get_columns(self, *args, **kwargs):
            # TODO: SAModelMixin duplicates this! Refactor the code.
            only_db_columns = kwargs.pop("only_db_columns", False)
            columns = [
                column_info(self, prop.key, prop.columns[0])
                for prop in class_mapper(self.model).iterate_properties
                if isinstance(prop, ColumnProperty) and len(prop.columns) == 1\
                   and not prop.key.startswith("_") and\
                   (not only_db_columns or isinstance(prop.columns[0], Column))
            ]
            if not only_db_columns:
                # If there's a mix, "real" DB columns should go first
                columns.sort(key=lambda c: c.db_column, reverse=True)
            return columns

    return SAModelView
