from __future__ import absolute_import
from flask.ext.toybox.sqlalchemy import SAModelMixin
from flask.ext.toybox.permissions import make_I
from flask import g
from . import db


I = make_I()


class User(db.Model, SAModelMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, info=I("r:staff+"))
    username = db.Column(db.String(32), unique=True, nullable=False, info=I("r:all"))
    first_name = db.Column(db.String(64), nullable=False, info=I("r:authenticated+,w:owner+"))
    last_name = db.Column(db.String(64), nullable=False, info=I("rw:owner+"))

    def check_permissions(self, user=None):
        user = getattr(g, "user", None)
        if user is not None:
            p = {"authenticated"}
            if user.id == self.id:
                p.add("owner")
            return p
        else:
            return {"anonymous"}

class Post(db.Model, SAModelMixin):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True, info=I("r:all"))
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), info=I("r:none"))
    date = db.Column(db.DateTime, info=I("r:all,w:owner+"))
    message = db.Column(db.Text, info=I("r:all,w:owner+"))
    user = db.relationship("User")
