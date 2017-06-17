# configitems.py - centralized declaration of configuration option
#
#  Copyright 2017 Pierre-Yves David <pierre-yves.david@octobus.net>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

from __future__ import absolute_import

import functools

from . import (
    error,
)

class configitem(object):
    """represent a known config item

    :section: the official config section where to find this item,
       :name: the official name within the section,
    :default: default value for this item,
    """

    def __init__(self, section, name, default=None):
        self.section = section
        self.name = name
        self.default = default

coreitems = {}

def _register(configtable, *args, **kwargs):
    item = configitem(*args, **kwargs)
    section = configtable.setdefault(item.section, {})
    if item.name in section:
        msg = "duplicated config item registration for '%s.%s'"
        raise error.ProgrammingError(msg % (item.section, item.name))
    section[item.name] = item

# Registering actual config items

def getitemregister(configtable):
    return functools.partial(_register, configtable)

coreconfigitem = getitemregister(coreitems)

coreconfigitem('patch', 'fuzz',
    default=2,
)
coreconfigitem('ui', 'clonebundleprefers',
    default=[],
)
coreconfigitem('ui', 'interactive',
    default=None,
)
coreconfigitem('ui', 'quiet',
    default=False,
)
