import unittest

from flask.ext.toybox import serialization
import collections
import datetime
import decimal

SpamTuple = collections.namedtuple("spam_tuple", "spam, eggs")

class SpamList(object):
    def __init__(self, data):
        self.data = data

    def as_list(self):
        return list(self.data)

class SpamDict(object):
    def __init__(self, data):
        self.data = data

    def as_dict(self):
        return dict(self.data)

class SpamJSON(object):
    def __init__(self, data):
        self.data = data

    def to_json(self):
        return self.data

class SerializationTestCase(unittest.TestCase):
    def test_json_encode_namedtuple(self):
        data = SpamTuple("spam_value", "eggs_value")
        serialized = serialization.JSON.serialize(data)
        reference = '{"spam": "spam_value", "eggs": "eggs_value"}'
        self.assertEqual(serialized, reference)

    def test_json_encode_to_json(self):
        data = SpamJSON("42")
        serialized = serialization.JSON.serialize(data)
        reference = '42'
        self.assertEqual(serialized, reference)

    def test_json_default(self):
        data = collections.OrderedDict([
            ("datetime", datetime.datetime(2012, 1, 1, 0, 0, 0, 0)),
            ("decimal", decimal.Decimal("4242.42424242424242424242")),
            ("as_list", SpamList((1, 2, 3))),
            ("as_dict", SpamDict({"spam": "spam_value", "eggs": "eggs_value"})),
            ("normal", [{"k": "v"}, 123])
        ])

        serialized = serialization.JSON.serialize(data)

        reference = ('{"datetime": "2012-01-01T00:00:00", '
                     '"decimal": "4242.42424242424242424242", '
                     '"as_list": [1, 2, 3], '
                     '"as_dict": {"eggs": "eggs_value", "spam": "spam_value"}, '
                     '"normal": [{"k": "v"}, 123]}')

        self.assertEqual(serialized, reference)
