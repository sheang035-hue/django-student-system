"""Project package.

Python 3.14 changed how ``copy.copy()`` handles ``super`` objects, which breaks
``BaseContext.__copy__`` in older Django releases.  The test client copies
template contexts, so apply a small, detection-based shim until the project runs
on a Django release that supports Python 3.14 natively.
"""

import sys

if sys.version_info >= (3, 14):
    from copy import copy

    from django.template.context import BaseContext

    try:
        copy(BaseContext())
    except AttributeError:
        def _base_context_copy(self):
            duplicate = BaseContext()
            duplicate.__class__ = self.__class__
            duplicate.__dict__ = copy(self.__dict__)
            duplicate.dicts = self.dicts[:]
            return duplicate

        BaseContext.__copy__ = _base_context_copy
