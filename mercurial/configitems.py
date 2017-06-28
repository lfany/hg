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

def loadconfigtable(ui, extname, configtable):
    """update config item known to the ui with the extension ones"""
    for section, items in configtable.items():
        knownitems = ui._knownconfig.setdefault(section, {})
        knownkeys = set(knownitems)
        newkeys = set(items)
        for key in sorted(knownkeys & newkeys):
            msg = "extension '%s' overwrite config item '%s.%s'"
            msg %= (extname, section, key)
            ui.develwarn(msg, config='warn-config')

        knownitems.update(items)

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

coreconfigitem('devel', 'all-warnings',
    default=False,
)
coreconfigitem('devel', 'bundle2.debug',
    default=False,
)
coreconfigitem('devel', 'check-locks',
    default=False,
)
coreconfigitem('devel', 'check-relroot',
    default=False,
)
coreconfigitem('devel', 'disableloaddefaultcerts',
    default=False,
)
coreconfigitem('devel', 'servercafile',
    default='',
)
coreconfigitem('devel', 'serverexactprotocol',
    default='',
)
coreconfigitem('devel', 'serverrequirecert',
    default=None,
)
coreconfigitem('devel', 'strip-obsmarkers',
    default=True,
)
coreconfigitem('patch', 'fuzz',
    default=2,
)
coreconfigitem('ui', 'clonebundleprefers',
    default=list,
)
coreconfigitem('ui', 'interactive',
    default=None,
)
coreconfigitem('ui', 'quiet',
    default=False,
)
