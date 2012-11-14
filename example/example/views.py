from __future__ import absolute_import
from flask.ext.toybox.sqlalchemy import saModelView
from flask.ext.toybox.views import BaseModelView
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.exceptions import NotFound
from .utils import class_route
from . import app, db
from . import models


SAModelView = saModelView(db.session)


class UserSubmodelView(SAModelView):
    def get_query(self, **kwargs):
        username = kwargs.pop("username")
        q = super(UserSubmodelView, self).get_query(**kwargs)
        return q.filter(self.model.user.has(username=username))

class UserSubmodelsView(BaseModelView):
    def fetch_object(self, username):
        try:
            user = db.session.query(models.User).filter_by(username=username).one()
        except NoResultFound:
            raise NotFound
        return db.session.query(self.model).filter_by(user=user).all()


@class_route("/", name="users")
class UsersView(BaseModelView):
    def fetch_object(self):
        q = db.session.query(models.User).values(models.User.username)
        return [row.username for row in q]

@class_route("/~<username>/", name="user")
class UserView(SAModelView):
    model = models.User

@class_route("/~<username>/posts/", name="user_posts")
class PostsView(UserSubmodelsView):
    model = models.Post

@class_route("/~<username>/posts/<id>", name="user_post")
class PostView(UserSubmodelView):
    model = models.Post
