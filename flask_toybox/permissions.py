from itertools import dropwhile
from functools import partial

DEFAULT_ACCESS_HIER = ["anonymous", "authenticated", "owner",
                       "staff", "admin", "system"]
DEFAULT_ACCESS_TARGETS = {"r": "readable", "w": "writeable"}

def I(access_hier, access_targets, access, **kwargs):
    """
    Consider obtaining a partial using convenience helper function `make_I`
    instead of calling this directly from your code.

    Note `"all"` and `"none"` are reserved level names that can't be used in
    `access_hier` list. Consider using synonyms like `"everyone"` or `"nobody"`,
    if you really need them.

    >>> I(DEFAULT_ACCESS_HIER, DEFAULT_ACCESS_TARGETS, "rw:owner,r:staff+")
    {"readable": set(["owner", "staff", "admin", "system"]),
     "writeable": set["owner"]}

    >>> I(DEFAULT_ACCESS_HIER, DEFAULT_ACCESS_TARGETS, "r:staff+")
    {"readable": set(["staff", "admin", "system"]),
     "writeable": set()}

    >>> I(DEFAULT_ACCESS_HIER, DEFAULT_ACCESS_TARGETS, "r:owner+,w:staff+")
    {"readable": set(["owner", "staff", "admin", "system"]),
     "writeable": set(["staff", "admin", "system"])}
    """
    # TODO: Properly document `I` function.
    info = kwargs.copy()
    info.update({"readable": set(), "writeable": set()})

    for name in access.split(","):
        name = name.strip()

        targets = "rw"
        if ":" in name:
            targets, name = name.split(":", 1)

        if name == "all":
            levels = set(access_hier)
        elif name == "none":
            levels = set([])
        elif name.endswith("+"):
            name = name[:-1]
            levels = set(dropwhile(lambda n: name != n, access_hier))
        else:
            levels = {name}

        for target in targets:
            info[access_targets[target]] |= levels

    return info

def make_I(hier=DEFAULT_ACCESS_HIER, targets=DEFAULT_ACCESS_TARGETS):
    """
    Returns a partial that makes using `I` more convenient.
    """
    return partial(I, hier, targets)

class ModelColumnInfo(object):
    """
    Class that holds the information about model's column.
    """
    def __init__(self, model, name, db_column=True, permissions=None):
        self.model = model
        self.name = name
        self.db_column = db_column
        self.permissions = permissions if permissions is not None else {}

    #def get_value(self):
    #    return getattr(self.model, self.name)
    #def set_value(self, value):
    #    setattr(self.model, self.name, value)
    #value = property(get_value, set_value)
