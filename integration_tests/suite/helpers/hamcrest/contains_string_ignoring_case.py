# Copyright 2011-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: BSD-3-Clause

# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

# Derived from https://github.com/hamcrest/PyHamcrest/blob/master/src/hamcrest/library/text/stringcontains.py

from hamcrest.library.text.substringmatcher import SubstringMatcher
from hamcrest.core.helpers.hasmethod import hasmethod

__author__ = "Jon Reid"
__copyright__ = "Copyright 2011 hamcrest.org"
__license__ = "SPDX-License-Identifier: BSD-3-Clause"


class StringContains(SubstringMatcher):
    def __init__(self, substring):
        super().__init__(substring)

    def _matches(self, item):
        if not hasmethod(item, 'lower'):
            return False
        return item.lower().find(self.substring.lower()) >= 0

    def relationship(self):
        return 'containing (ignoring case)'


def contains_string_ignoring_case(substring):
    """Matches if object is a string containing a given string, ignoring case.
    :param string: The string to search for.
    This matcher first checks whether the evaluated object is a string. If so,
    it checks whether it contains ``string``, ignoring case differences.
    Example::
        contains_string("deF")
    will match "abcDefg".
    """
    return StringContains(substring)
