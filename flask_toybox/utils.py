import string
from functools import partial

def is_printable(value):
    """
    Returns True if value is a string, containing only printable characters.
    Returns False otherwise.
    """
    return isinstance(value, basestring) \
           and all(c in string.printable for c in value)

# Taken from http://www.daniweb.com/software-development/python/code/406393/
class mixedmethod(object):
    """
    This decorator mutates a function defined in a class into a 'mixed' class and instance method.

    Usage:

        class Spam:
            @mixedmethod
            def egg(self, cls, *args, **kwargs):
                if self is None:
                    pass # executed if egg was called as a class method (eg. Spam.egg())
                else:
                    pass # executed if egg was called as an instance method (eg. instance.egg())

    The decorated methods need 2 implicit arguments: self and cls, the former being None when
    there is no instance in the call. This follows the same rule as __get__ methods in python's
    descriptor protocol.
    """
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, cls):
        return partial(self.func, instance, cls)
