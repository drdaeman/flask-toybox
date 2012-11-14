from __future__ import absolute_import
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.toybox import ToyBox


app = Flask(__name__)
app.config.from_object("example.settings.DevelopmentConfig")

db = SQLAlchemy(app)
toybox = ToyBox(app)


from . import auth
from . import views
