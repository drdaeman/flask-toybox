"""
Cross-version compatibility module.
"""

from __future__ import absolute_import
try:
    from collections import OrderedDict
except ImportError: # pragma: no cover
    from ordereddict import OrderedDict
