""" Object inspection utilities.
"""
def _getattr_recursive(obj, attr):
    try: return getattr(obj, attr)
    except AttributeError:
        for cls in obj.__bases__:
            try: return _getattr_recursive(cls, attr)
            except AttributeError: continue

def get_members(obj, predicate=None):
    """ Replacement for inspect.getmembers.
    @return: Dictionary of members.
    """
    mems = {}
    for attr in dir(obj):
        val = _getattr_recursive(obj, attr)
        if predicate is None or predicate(val):
            mems[attr] = val
    return mems