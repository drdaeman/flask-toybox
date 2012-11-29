from __future__ import absolute_import
from flask.ext.toybox.sqlalchemy import SAModelView, SACollectionView
from flask.ext.toybox.views import BaseModelView
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.exceptions import NotFound
from .utils import class_route
from . import app, db
from . import models


class UserSubmodelMixin(object):
    def get_query(self, **kwargs):
        username = kwargs.pop("username")
        q = super(UserSubmodelMixin, self).get_query(**kwargs)
        return q.filter(self.model.user.has(username=username))


@class_route("/", name="users")
class UsersView(SACollectionView):
    model = models.User

@class_route("/~<username>/", name="user")
class UserView(SAModelView):
    model = models.User

@class_route("/~<username>/posts/", name="user_posts")
class PostsView(UserSubmodelMixin, SACollectionView):
    model = models.Post

@class_route("/~<username>/posts/<id>", name="user_post")
class PostView(UserSubmodelMixin, SAModelView):
    model = models.Post
