"""
Cross-version compatibility module.
"""

from __future__ import absolute_import
try:
    from collections import OrderedDict
except ImportError: # pragma: no cover
    from ordereddict import OrderedDict

# PATCH method was recognized only in Flask 0.9+, so monkey patching is needed
# for older versions. Not pretty, but does the job and shouldn't have any
# bad consequences.

import flask.views
if not "patch" in flask.views.http_method_funcs:
    flask.views.http_method_funcs = frozenset(
            list(flask.views.http_method_funcs) + ["patch"])
