import unittest

from flask.ext.toybox.views import BaseModelView, ModelView
from flask.ext.toybox.permissions import make_I, DEFAULT_ACCESS_HIER, ModelColumnInfo
from flask.ext.toybox import ToyBox
from flask import Flask, g
import json

DUMMY_DATA = {
    "spam": "spam_value",
    "eggs": "eggs_value"
}

I = make_I()
class DummyModel(object):
    permissions_test = [
        I("r:authenticated+,w:owner"),
        I("r:all,w:none"),
    ]

    def __init__(self, data):
        self.data = data

    def as_dict(self):
        return self.data

    #def check_permissions(self):
    #    return frozenset([])

    def get_columns(self, **kwargs):
        return {ModelColumnInfo(self, "spam"),
                ModelColumnInfo(self, "eggs")}

class DummyBaseModelView(BaseModelView):
    def fetch_object(self, *args, **kwargs):
        obj = DummyModel(DUMMY_DATA)
        g.etagger.set_object(obj)
        return obj

class DummyModelView(ModelView):
    def fetch_object(self, *args, **kwargs):
        obj = DummyModel(DUMMY_DATA)
        g.etagger.set_object(obj)
        return obj

class SimpleModelTestCase(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.debug = True
        toybox = ToyBox(app)
        app.add_url_rule("/test", view_func=DummyModelView.as_view("test"))
        app.add_url_rule("/test-base", view_func=DummyBaseModelView.as_view("test_base"))
        self.app = app.test_client()

    def test_permission_calc(self):
        reference = [
            {
                "readable": {"authenticated", "owner", "staff",
                             "admin", "system"},
                "writeable": {"owner"},
            },
            {
                "readable": set(DEFAULT_ACCESS_HIER),
                "writeable": set(),
            },
        ]
        self.assertEqual(DummyModel.permissions_test, reference)

    def test_get(self):
        for url in ("/test", "/test-base"):
            response = self.app.get(url, headers={"Accept": "application/json"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data), DUMMY_DATA)
            etag = response.headers.get("ETag", None)
            self.assertIsNotNone(etag)
            response = self.app.get("/test", headers={
                "Accept": "application/json",
                "If-None-Match": etag
            })
            self.assertEqual(response.status_code, 304, response.data)

    def test_patch(self):
        response = self.app.get("/test", headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), DUMMY_DATA)
        etag = response.headers.get("ETag", None)
        self.assertIsNotNone(etag)

        response = self.app.patch(
            "/test",
            headers={
                "Accept": "application/json",
                "If-Match": etag
            },
            data=json.dumps({"spam": "Spam Spam Spam"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 204, response.data)

    def test_base_is_readonly(self):
        for method in (self.app.post, self.app.patch, self.app.put, self.app.delete):
            response = method("/test-base", headers={"Accept": "application/json"})
            self.assertEqual(response.status_code, 405,
                             "BaseModelView allowed {0}".format(method.__name__.upper()))
