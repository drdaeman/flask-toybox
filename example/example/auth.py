from __future__ import absolute_import

from sqlalchemy.orm.exc import NoResultFound
from flask import g, request
from . import app
from .models import User

@app.before_request
def before_request():
    """
    Very silly and insecure authentication system.

    Use ``?user=<username>`` in URL to authenticate as specified user.
    """
    if "auth" in request.args:
        try:
            g.user = User.query.filter_by(username=request.args["auth"]).one()
        except NoResultFound:
            g.user = None
    else:
        g.user = None
