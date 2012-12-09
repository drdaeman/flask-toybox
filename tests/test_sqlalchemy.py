import unittest

from flask.ext.toybox.sqlalchemy import SAModelMixin, SAModelView, SACollectionView, PaginableByNumber, QueryFiltering
from flask.ext.toybox.permissions import make_I
from flask.ext.toybox import ToyBox
from flask import Flask, g, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean
import json

Base = declarative_base()

I = make_I()
class User(Base, SAModelMixin):
    __tablename__ = "test_users"

    id = Column(Integer, primary_key=True)
    username = Column(String, info=I("r:all,w:none"))
    fullname = Column(String, info=I("rw:all"))
    email = Column(String, info=I("rw:owner+"))
    badges = Column(Integer, default=0, info=I("r:all,w:staff+"))
    is_active = Column(Boolean, default=True, info=I("r:all,w:staff+"))
    is_staff = Column(Boolean, default=False, info=I("r:staff+,w:admin+"))

    def __init__(self, username, fullname, email, **kwargs):
        self.username = username
        self.fullname = fullname
        self.email = email
        for name, value in kwargs.items():
            setattr(self, name, value)

    def check_instance_permissions(self, user=None):
        # Very silly a12n.
        auth = request.args.get("auth", "")
        if auth != "":
            user = Session.object_session(self).query(User).filter_by(username=auth).one()
            return set(["owner"]) if user.id == self.id else set(["authenticated"])
        else:
            return set(["anonymous"])

    def __repr__(self):
        return "<{0}: {1}, {2}>".format(self.__class__.__name__,
                                        self.username, self.fullname)

class SQLAlchemyModelTestCase(unittest.TestCase):
    def setUp(self):
        # Set up SQLAlchemy models
        engine = create_engine('sqlite:///:memory:', echo=False)
        Base.metadata.create_all(engine)
        ScopedSession = scoped_session(sessionmaker(bind=engine))

        # Create some models
        db_session = ScopedSession()
        db_session.add(User("spam", "Spam", "spam@users.example.org", badges=1, is_staff=True))
        db_session.add(User("ham", "Ham", "ham@users.example.org", is_active=False))
        db_session.add(User("eggs", "Eggs", "eggs@users.example.org", badges=2, is_staff=True))
        db_session.commit()
        self.db_session = db_session

        # Set up Flask
        app = Flask(__name__)
        app.debug = True
        self.real_app = app

        # Set up ToyBox
        toybox = ToyBox(app)

        class UserView(SAModelView):
            model = User
            query_class = db_session.query

            def save_object(self, obj):
                # In a real code, this should be done by a middleware/wrapper.
                # However, this is a test, so we simplify things a bit.
                # Don't commit from here in production!
                db_session.commit()
        app.add_url_rule("/users/<username>", view_func=UserView.as_view("user"))

        class UsersView(PaginableByNumber, QueryFiltering, SACollectionView):
            model = User
            query_class = db_session.query
            order_by = "username"
        app.add_url_rule("/users/", view_func=UsersView.as_view("users"))

        self.app = app.test_client()

    def test_get(self):
        response = self.app.get("/users/spam", headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200, response.status)

        reference = {"username": "spam", "fullname": "Spam"}
        data = json.loads(response.data)
        for k, v in reference.items():
            self.assertEqual(data[k], v)

        etag = response.headers.get("ETag", None)
        self.assertTrue(etag is not None)
        response = self.app.get("/users/spam", headers={
            "Accept": "application/json",
            "If-None-Match": etag
        })
        self.assertEqual(response.status_code, 304, response.status)

    def test_get_collection(self):
        response = self.app.get("/users/", headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200, response.status)

        reference = [{u"username": u"spam", u"fullname": u"Spam"},
                     {u"username": u"ham",  u"fullname": u"Ham"},
                     {u"username": u"eggs", u"fullname": u"Eggs"}]
        data = json.loads(response.data)
        for ref_item in reference:
            self.assertTrue(any(all(data_item[k] == v for k, v in ref_item.items()) for data_item in data), "Not found: {0!r}".format(ref_item))
        for data_item in data:
            self.assertTrue(data_item.get("email", None) is None)

        etag = response.headers.get("ETag", None)
        self.assertTrue(etag is not None)
        response = self.app.get("/users/", headers={
            "Accept": "application/json",
            "If-None-Match": etag
        })
        self.assertEqual(response.status_code, 304, response.status)

    def test_collection_pagination(self):
        response = self.app.get("/users/", headers={"Accept": "application/json", "Range": "items=1-10"})
        self.assertEqual(response.status_code, 206, response.status)
        content_range = response.headers.get("Content-Range", "")
        self.assertTrue(content_range.startswith("items 1-2/"), content_range)

        data = json.loads(response.data)
        usernames = [data_item.get("username", None) for data_item in data]
        self.assertEqual(usernames, ["ham", "spam"])

    def test_collection_filtering(self):
        cases = [
            # This also tests whenever is_admin will be ignored, as it is not readable.
            ("is_staff=true&is_admin=true&spam=spam", set(["spam", "eggs"])),
            ("badges=lt:2", set(["ham", "spam"])),
            ("badges=eq:0&is_active=false", set(["ham"])),
            ("badges=ne:0&is_active=false", set()),
            ("is_staff=true&is_staff=false", set()),
            ("badges=ne:null", set(["spam", "ham", "eggs"])),
            ("is_staff=\"true\"", set()), # XXX: Should it return empty set or error?
            ("is_staff=invalid", set())
        ]

        for query, expected in cases:
            response = self.app.get("/users/?" + query, headers={"Accept": "application/json"})
            self.assertEqual(response.status_code, 200, response.status)
            data = json.loads(response.data)
            usernames = set([data_item.get("username", None) for data_item in data])
            self.assertEqual(usernames, expected)

    def test_collection_is_readonly(self):
        for method in ("put", "patch", "delete"):
            response = getattr(self.app, method)("/users/", headers={"Accept": "application/json"})
            self.assertEquals(response.status_code, 405, "Method {0} yielded {1}".format(method.upper(), response.status))

    def test_get_collection_permissions(self):
        for username in ("", "spam", "ham", "eggs"):
            response = self.app.get("/users/?auth=" + username, headers={"Accept": "application/json"})
            self.assertEqual(response.status_code, 200, response.status)
            data = json.loads(response.data)
            for data_item in data:
                if data_item["username"] == username:
                    self.assertEqual(data_item.get("email", None), username + "@users.example.org")
                else:
                    self.assertTrue(data_item.get("email", None) is None)

    def test_patch(self):
        response = self.app.get("/users/eggs",
                                headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertTrue("username" in data)
        self.assertTrue("fullname" in data)
        self.assertEqual(data["username"], "eggs")

        etag = response.headers.get("ETag", None)
        self.assertTrue(etag is not None)

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
        self.assertTrue("username" in data)
        self.assertTrue("fullname" in data)
        self.assertEqual(data["fullname"], "Python Eggs")

    def test_patch_non_writeable(self):
        response = self.app.get("/users/eggs",
                                headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200)

        etag = response.headers.get("ETag", None)
        self.assertTrue(etag is not None)
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