import unittest

from flask.ext.toybox.sqlalchemy import SAModelMixin, saModelView
from flask.ext.toybox.permissions import make_I
from flask.ext.toybox import ToyBox
from flask import Flask, g
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
import json

Base = declarative_base()

I = make_I()
class User(Base, SAModelMixin):
    __tablename__ = "test_users"

    id = Column(Integer, primary_key=True)
    username = Column(String, info=I("r:all,w:none"))
    fullname = Column(String, info=I("rw:all"))

    def __init__(self, username, fullname):
        self.username = username
        self.fullname = fullname

    def __repr__(self):
        return "<{0}: {1}, {2}>".format(self.__class__.__name__,
                                        self.username, self.fullname)

class SQLAlchemyModelTestCase(unittest.TestCase):
    def setUp(self):
        # Set up SQLAlchemy models
        engine = create_engine('sqlite:///:memory:', echo=False)
        Base.metadata.create_all(engine)
        Session = scoped_session(sessionmaker(bind=engine))

        # Create some models
        db_session = Session()
        db_session.add(User("spam", "Spam"))
        db_session.add(User("ham", "Ham"))
        db_session.add(User("eggs", "Eggs"))
        db_session.commit()

        # Set up Flask
        app = Flask(__name__)
        app.debug = True

        # Set up ToyBox
        toybox = ToyBox(app)

        class UserView(saModelView(db_session)):
            model = User

            #def fetch_object(self, username):
            #    obj = db_session.query(User).filter_by(username=username).one()
            #    g.etagger.set_object(obj)
            #    return obj
            def save_object(self, obj):
                # In a real code, this should be done by a middleware/wrapper.
                # However, this is a test, so we simplify things a bit.
                # Don't commit from here in production!
                db_session.commit()
        app.add_url_rule("/users/<username>", view_func=UserView.as_view("user"))

        self.app = app.test_client()

    def test_get(self):
        response = self.app.get("/users/spam", headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200, response.status)

        reference = {"username": "spam", "fullname": "Spam"}
        data = json.loads(response.data)
        for k, v in reference.items():
            self.assertEqual(data[k], v)

        etag = response.headers.get("ETag", None)
        self.assertIsNotNone(etag)
        response = self.app.get("/users/spam", headers={
            "Accept": "application/json",
            "If-None-Match": etag
        })
        self.assertEqual(response.status_code, 304, response.status)

    def test_patch(self):
        response = self.app.get("/users/eggs",
                                headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn("username", data)
        self.assertIn("fullname", data)
        self.assertEqual(data["username"], "eggs")

        etag = response.headers.get("ETag", None)
        self.assertIsNotNone(etag)

        response = self.app.patch(
            "/users/eggs",
            headers={"Accept": "application/json",},
            data=json.dumps({"fullname": "Python Eggs"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 428, response.status)

        response = self.app.patch(
            "/users/eggs",
            headers={
                "Accept": "application/json",
                "If-Match": etag
            },
            data = json.dumps({"fullname": "Python Eggs"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 204, response.data)
        response = self.app.get("/users/eggs",
                                headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200, response.status)
        data = json.loads(response.data)
        self.assertIn("username", data)
        self.assertIn("fullname", data)
        self.assertEqual(data["fullname"], "Python Eggs")

    def test_patch_non_writeable(self):
        response = self.app.get("/users/eggs",
                                headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200)

        etag = response.headers.get("ETag", None)
        self.assertIsNotNone(etag)
        response = self.app.patch(
            "/users/eggs",
            headers={
                "Accept": "application/json",
                "If-Match": etag
            },
            data = json.dumps({"username": "eggs2"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 422, response.data)

        response = self.app.get("/users/eggs",
                                headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200, response.status)