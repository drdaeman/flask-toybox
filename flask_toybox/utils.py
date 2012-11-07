import string

def is_printable(value):
    """
    Returns True if value is a string, containing only printable characters.
    Returns False otherwise.
    """
    return isinstance(value, basestring) \
           and all(c in string.printable for c in value)
