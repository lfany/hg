# repoview.py - Filtered view of a localrepo object
#
# Copyright 2012 Pierre-Yves David <pierre-yves.david@ens-lyon.org>
#                Logilab SA        <contact@logilab.fr>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

import copy
import phases

def computeunserved(repo):
    """compute the set of revision that should be filtered when used a server

    Secret and hidden changeset should not pretend to be here."""
    assert not repo.changelog.filteredrevs
    # fast path in simple case to avoid impact of non optimised code
    if phases.hassecret(repo) or repo.obsstore:
        return frozenset(repo.revs('hidden() + secret()'))
    return ()

# function to compute filtered set
filtertable = {'unserved': computeunserved}

def filteredrevs(repo, filtername):
    """returns set of filtered revision for this filter name"""
    if filtername not in repo.filteredrevcache:
        func = filtertable[filtername]
        repo.filteredrevcache[filtername] = func(repo.unfiltered())
    return repo.filteredrevcache[filtername]

class repoview(object):
    """Provide a read/write view of a repo through a filtered changelog

    This object is used to access a filtered version of a repository without
    altering the original repository object itself. We can not alter the
    original object for two main reasons:
    - It prevents the use of a repo with multiple filters at the same time. In
      particular when multiple threads are involved.
    - It makes scope of the filtering harder to control.

    This object behaves very closely to the original repository. All attribute
    operations are done on the original repository:
    - An access to `repoview.someattr` actually returns `repo.someattr`,
    - A write to `repoview.someattr` actually sets value of `repo.someattr`,
    - A deletion of `repoview.someattr` actually drops `someattr`
      from `repo.__dict__`.

    The only exception is the `changelog` property. It is overridden to return
    a (surface) copy of `repo.changelog` with some revisions filtered. The
    `filtername` attribute of the view control the revisions that need to be
    filtered.  (the fact the changelog is copied is an implementation detail).

    Unlike attributes, this object intercepts all method calls. This means that
    all methods are run on the `repoview` object with the filtered `changelog`
    property. For this purpose the simple `repoview` class must be mixed with
    the actual class of the repository. This ensures that the resulting
    `repoview` object have the very same methods than the repo object. This
    leads to the property below.

        repoview.method() --> repo.__class__.method(repoview)

    The inheritance has to be done dynamically because `repo` can be of any
    subclasses of `localrepo`. Eg: `bundlerepo` or `httprepo`.
    """

    def __init__(self, repo, filtername):
        object.__setattr__(self, '_unfilteredrepo', repo)
        object.__setattr__(self, 'filtername', filtername)

    # not a cacheproperty on purpose we shall implement a proper cache later
    @property
    def changelog(self):
        """return a filtered version of the changeset

        this changelog must not be used for writing"""
        # some cache may be implemented later
        cl = copy.copy(self._unfilteredrepo.changelog)
        cl.filteredrevs = filteredrevs(self._unfilteredrepo, self.filtername)
        return cl

    def unfiltered(self):
        """Return an unfiltered version of a repo"""
        return self._unfilteredrepo

    def filtered(self, name):
        """Return a filtered version of a repository"""
        if name == self.filtername:
            return self
        return self.unfiltered().filtered(name)

    # everything access are forwarded to the proxied repo
    def __getattr__(self, attr):
        return getattr(self._unfilteredrepo, attr)

    def __setattr__(self, attr, value):
        return setattr(self._unfilteredrepo, attr, value)

    def __delattr__(self, attr):
        return delattr(self._unfilteredrepo, attr)

    # The `requirement` attribut is initialiazed during __init__. But
    # __getattr__ won't be called as it also exists on the class. We need
    # explicit forwarding to main repo here
    @property
    def requirements(self):
        return self._unfilteredrepo.requirements

