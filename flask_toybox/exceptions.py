"""
This module describes various helpful exceptions, that may happen
during API lifetime.
"""

from werkzeug.exceptions import HTTPException
from flask import redirect, Response

class UnprocessableEntity(HTTPException):
    """
    The 422 (Unprocessable Entity) status code means the server understands the
    content type of the request entity (hence a 415 (Unsupported Media Type)
    status code is inappropriate), and the syntax of the request entity is
    correct (thus a 400 (Bad Request) status code is inappropriate) but was
    unable to process the contained instructions.

    For example, this error condition may occur if an XML request body contains
    well-formed (i.e., syntactically correct), but semantically erroneous,
    XML instructions.
    """
    code = 422
    description = "<p>Unprocessable Entity.</p>"

class NotModified(HTTPException):
    """
    If the client has performed a conditional GET request and access is
    allowed, but the document has not been modified, the server SHOULD
    respond with this status code. The 304 response MUST NOT contain a
    message-body, and thus is always terminated by the first empty line
    after the header fields.
    """
    code = 304
    def get_response(self, environment):
        return Response(status=304)

class PreconditionRequired(HTTPException):
    """
    The 428 status code indicates that the origin server requires the
    request to be conditional.

    Its typical use is to avoid the "lost update" problem, where a client
    GETs a resource's state, modifies it, and PUTs it back to the server,
    when meanwhile a third party has modified the state on the server,
    leading to a conflict.  By requiring requests to be conditional, the
    server can assure that clients are working with the correct copies.
    """
    code = 428
    description = ('<p>This request is required to be '
                   'conditional; try using "If-Match".</p>')
    name = "Precondition Required"

    def get_response(self, environment):
        resp = super(PreconditionRequired, self).get_response(environment)
        resp.status = str(self.code) + " " + self.name.upper()
        return resp

class Redirect(HTTPException):
    """
    HTTP redirect (30x codes) as exception.
    """
    def __init__(self, location, code=307):
        self.location = location
        self.code = code
        super(Redirect, self).__init__()

    def get_response(self, environment):
        return redirect(self.location, self.code)

def abort_redirect(location, code=307):
    raise Redirect(location, code)
