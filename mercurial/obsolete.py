# obsolete.py - obsolete markers handling
#
# Copyright 2012 Pierre-Yves David <pierre-yves.david@ens-lyon.org>
#                Logilab SA        <contact@logilab.fr>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

"""Obsolete marker handling

An obsolete marker maps an old changeset to a list of new
changesets. If the list of new changesets is empty, the old changeset
is said to be "killed". Otherwise, the old changeset is being
"replaced" by the new changesets.

Obsolete markers can be used to record and distribute changeset graph
transformations performed by history rewrite operations, and help
building new tools to reconcile conflicting rewrite actions. To
facilitate conflict resolution, markers include various annotations
besides old and news changeset identifiers, such as creation date or
author name.

The old obsoleted changeset is called a "precursor" and possible
replacements are called "successors". Markers that used changeset X as
a precursor are called "successor markers of X" because they hold
information about the successors of X. Markers that use changeset Y as
a successors are call "precursor markers of Y" because they hold
information about the precursors of Y.

Examples:

- When changeset A is replaced by changeset A', one marker is stored:

    (A, (A',))

- When changesets A and B are folded into a new changeset C, two markers are
  stored:

    (A, (C,)) and (B, (C,))

- When changeset A is simply "pruned" from the graph, a marker is created:

    (A, ())

- When changeset A is split into B and C, a single marker is used:

    (A, (B, C))

  We use a single marker to distinguish the "split" case from the "divergence"
  case. If two independent operations rewrite the same changeset A in to A' and
  A'', we have an error case: divergent rewriting. We can detect it because
  two markers will be created independently:

  (A, (B,)) and (A, (C,))

Format
------

Markers are stored in an append-only file stored in
'.hg/store/obsstore'.

The file starts with a version header:

- 1 unsigned byte: version number, starting at zero.

The header is followed by the markers. Marker format depend of the version. See
comment associated with each format for details.

"""
from __future__ import absolute_import

import errno
import struct

from .i18n import _
from . import (
    error,
    node,
    phases,
    policy,
    util,
)

parsers = policy.importmod(r'parsers')

_pack = struct.pack
_unpack = struct.unpack
_calcsize = struct.calcsize
propertycache = util.propertycache

# the obsolete feature is not mature enough to be enabled by default.
# you have to rely on third party extension extension to enable this.
_enabled = False

# Options for obsolescence
createmarkersopt = 'createmarkers'
allowunstableopt = 'allowunstable'
exchangeopt = 'exchange'

def isenabled(repo, option):
    """Returns True if the given repository has the given obsolete option
    enabled.
    """
    result = set(repo.ui.configlist('experimental', 'evolution'))
    if 'all' in result:
        return True

    # For migration purposes, temporarily return true if the config hasn't been
    # set but _enabled is true.
    if len(result) == 0 and _enabled:
        return True

    # createmarkers must be enabled if other options are enabled
    if ((allowunstableopt in result or exchangeopt in result) and
        not createmarkersopt in result):
        raise error.Abort(_("'createmarkers' obsolete option must be enabled "
                           "if other obsolete options are enabled"))

    return option in result

### obsolescence marker flag

## bumpedfix flag
#
# When a changeset A' succeed to a changeset A which became public, we call A'
# "bumped" because it's a successors of a public changesets
#
# o    A' (bumped)
# |`:
# | o  A
# |/
# o    Z
#
# The way to solve this situation is to create a new changeset Ad as children
# of A. This changeset have the same content than A'. So the diff from A to A'
# is the same than the diff from A to Ad. Ad is marked as a successors of A'
#
# o   Ad
# |`:
# | x A'
# |'|
# o | A
# |/
# o Z
#
# But by transitivity Ad is also a successors of A. To avoid having Ad marked
# as bumped too, we add the `bumpedfix` flag to the marker. <A', (Ad,)>.
# This flag mean that the successors express the changes between the public and
# bumped version and fix the situation, breaking the transitivity of
# "bumped" here.
bumpedfix = 1
usingsha256 = 2

## Parsing and writing of version "0"
#
# The header is followed by the markers. Each marker is made of:
#
# - 1 uint8 : number of new changesets "N", can be zero.
#
# - 1 uint32: metadata size "M" in bytes.
#
# - 1 byte: a bit field. It is reserved for flags used in common
#   obsolete marker operations, to avoid repeated decoding of metadata
#   entries.
#
# - 20 bytes: obsoleted changeset identifier.
#
# - N*20 bytes: new changesets identifiers.
#
# - M bytes: metadata as a sequence of nul-terminated strings. Each
#   string contains a key and a value, separated by a colon ':', without
#   additional encoding. Keys cannot contain '\0' or ':' and values
#   cannot contain '\0'.
_fm0version = 0
_fm0fixed   = '>BIB20s'
_fm0node = '20s'
_fm0fsize = _calcsize(_fm0fixed)
_fm0fnodesize = _calcsize(_fm0node)

def _fm0readmarkers(data, off):
    # Loop on markers
    l = len(data)
    while off + _fm0fsize <= l:
        # read fixed part
        cur = data[off:off + _fm0fsize]
        off += _fm0fsize
        numsuc, mdsize, flags, pre = _unpack(_fm0fixed, cur)
        # read replacement
        sucs = ()
        if numsuc:
            s = (_fm0fnodesize * numsuc)
            cur = data[off:off + s]
            sucs = _unpack(_fm0node * numsuc, cur)
            off += s
        # read metadata
        # (metadata will be decoded on demand)
        metadata = data[off:off + mdsize]
        if len(metadata) != mdsize:
            raise error.Abort(_('parsing obsolete marker: metadata is too '
                               'short, %d bytes expected, got %d')
                             % (mdsize, len(metadata)))
        off += mdsize
        metadata = _fm0decodemeta(metadata)
        try:
            when, offset = metadata.pop('date', '0 0').split(' ')
            date = float(when), int(offset)
        except ValueError:
            date = (0., 0)
        parents = None
        if 'p2' in metadata:
            parents = (metadata.pop('p1', None), metadata.pop('p2', None))
        elif 'p1' in metadata:
            parents = (metadata.pop('p1', None),)
        elif 'p0' in metadata:
            parents = ()
        if parents is not None:
            try:
                parents = tuple(node.bin(p) for p in parents)
                # if parent content is not a nodeid, drop the data
                for p in parents:
                    if len(p) != 20:
                        parents = None
                        break
            except TypeError:
                # if content cannot be translated to nodeid drop the data.
                parents = None

        metadata = tuple(sorted(metadata.iteritems()))

        yield (pre, sucs, flags, metadata, date, parents)

def _fm0encodeonemarker(marker):
    pre, sucs, flags, metadata, date, parents = marker
    if flags & usingsha256:
        raise error.Abort(_('cannot handle sha256 with old obsstore format'))
    metadata = dict(metadata)
    time, tz = date
    metadata['date'] = '%r %i' % (time, tz)
    if parents is not None:
        if not parents:
            # mark that we explicitly recorded no parents
            metadata['p0'] = ''
        for i, p in enumerate(parents, 1):
            metadata['p%i' % i] = node.hex(p)
    metadata = _fm0encodemeta(metadata)
    numsuc = len(sucs)
    format = _fm0fixed + (_fm0node * numsuc)
    data = [numsuc, len(metadata), flags, pre]
    data.extend(sucs)
    return _pack(format, *data) + metadata

def _fm0encodemeta(meta):
    """Return encoded metadata string to string mapping.

    Assume no ':' in key and no '\0' in both key and value."""
    for key, value in meta.iteritems():
        if ':' in key or '\0' in key:
            raise ValueError("':' and '\0' are forbidden in metadata key'")
        if '\0' in value:
            raise ValueError("':' is forbidden in metadata value'")
    return '\0'.join(['%s:%s' % (k, meta[k]) for k in sorted(meta)])

def _fm0decodemeta(data):
    """Return string to string dictionary from encoded version."""
    d = {}
    for l in data.split('\0'):
        if l:
            key, value = l.split(':')
            d[key] = value
    return d

## Parsing and writing of version "1"
#
# The header is followed by the markers. Each marker is made of:
#
# - uint32: total size of the marker (including this field)
#
# - float64: date in seconds since epoch
#
# - int16: timezone offset in minutes
#
# - uint16: a bit field. It is reserved for flags used in common
#   obsolete marker operations, to avoid repeated decoding of metadata
#   entries.
#
# - uint8: number of successors "N", can be zero.
#
# - uint8: number of parents "P", can be zero.
#
#     0: parents data stored but no parent,
#     1: one parent stored,
#     2: two parents stored,
#     3: no parent data stored
#
# - uint8: number of metadata entries M
#
# - 20 or 32 bytes: precursor changeset identifier.
#
# - N*(20 or 32) bytes: successors changesets identifiers.
#
# - P*(20 or 32) bytes: parents of the precursors changesets.
#
# - M*(uint8, uint8): size of all metadata entries (key and value)
#
# - remaining bytes: the metadata, each (key, value) pair after the other.
_fm1version = 1
_fm1fixed = '>IdhHBBB20s'
_fm1nodesha1 = '20s'
_fm1nodesha256 = '32s'
_fm1nodesha1size = _calcsize(_fm1nodesha1)
_fm1nodesha256size = _calcsize(_fm1nodesha256)
_fm1fsize = _calcsize(_fm1fixed)
_fm1parentnone = 3
_fm1parentshift = 14
_fm1parentmask = (_fm1parentnone << _fm1parentshift)
_fm1metapair = 'BB'
_fm1metapairsize = _calcsize('BB')

def _fm1purereadmarkers(data, off):
    # make some global constants local for performance
    noneflag = _fm1parentnone
    sha2flag = usingsha256
    sha1size = _fm1nodesha1size
    sha2size = _fm1nodesha256size
    sha1fmt = _fm1nodesha1
    sha2fmt = _fm1nodesha256
    metasize = _fm1metapairsize
    metafmt = _fm1metapair
    fsize = _fm1fsize
    unpack = _unpack

    # Loop on markers
    stop = len(data) - _fm1fsize
    ufixed = struct.Struct(_fm1fixed).unpack

    while off <= stop:
        # read fixed part
        o1 = off + fsize
        t, secs, tz, flags, numsuc, numpar, nummeta, prec = ufixed(data[off:o1])

        if flags & sha2flag:
            # FIXME: prec was read as a SHA1, needs to be amended

            # read 0 or more successors
            if numsuc == 1:
                o2 = o1 + sha2size
                sucs = (data[o1:o2],)
            else:
                o2 = o1 + sha2size * numsuc
                sucs = unpack(sha2fmt * numsuc, data[o1:o2])

            # read parents
            if numpar == noneflag:
                o3 = o2
                parents = None
            elif numpar == 1:
                o3 = o2 + sha2size
                parents = (data[o2:o3],)
            else:
                o3 = o2 + sha2size * numpar
                parents = unpack(sha2fmt * numpar, data[o2:o3])
        else:
            # read 0 or more successors
            if numsuc == 1:
                o2 = o1 + sha1size
                sucs = (data[o1:o2],)
            else:
                o2 = o1 + sha1size * numsuc
                sucs = unpack(sha1fmt * numsuc, data[o1:o2])

            # read parents
            if numpar == noneflag:
                o3 = o2
                parents = None
            elif numpar == 1:
                o3 = o2 + sha1size
                parents = (data[o2:o3],)
            else:
                o3 = o2 + sha1size * numpar
                parents = unpack(sha1fmt * numpar, data[o2:o3])

        # read metadata
        off = o3 + metasize * nummeta
        metapairsize = unpack('>' + (metafmt * nummeta), data[o3:off])
        metadata = []
        for idx in xrange(0, len(metapairsize), 2):
            o1 = off + metapairsize[idx]
            o2 = o1 + metapairsize[idx + 1]
            metadata.append((data[off:o1], data[o1:o2]))
            off = o2

        yield (prec, sucs, flags, tuple(metadata), (secs, tz * 60), parents)

def _fm1encodeonemarker(marker):
    pre, sucs, flags, metadata, date, parents = marker
    # determine node size
    _fm1node = _fm1nodesha1
    if flags & usingsha256:
        _fm1node = _fm1nodesha256
    numsuc = len(sucs)
    numextranodes = numsuc
    if parents is None:
        numpar = _fm1parentnone
    else:
        numpar = len(parents)
        numextranodes += numpar
    formatnodes = _fm1node * numextranodes
    formatmeta = _fm1metapair * len(metadata)
    format = _fm1fixed + formatnodes + formatmeta
    # tz is stored in minutes so we divide by 60
    tz = date[1]//60
    data = [None, date[0], tz, flags, numsuc, numpar, len(metadata), pre]
    data.extend(sucs)
    if parents is not None:
        data.extend(parents)
    totalsize = _calcsize(format)
    for key, value in metadata:
        lk = len(key)
        lv = len(value)
        data.append(lk)
        data.append(lv)
        totalsize += lk + lv
    data[0] = totalsize
    data = [_pack(format, *data)]
    for key, value in metadata:
        data.append(key)
        data.append(value)
    return ''.join(data)

def _fm1readmarkers(data, off):
    native = getattr(parsers, 'fm1readmarkers', None)
    if not native:
        return _fm1purereadmarkers(data, off)
    stop = len(data) - _fm1fsize
    return native(data, off, stop)

# mapping to read/write various marker formats
# <version> -> (decoder, encoder)
formats = {_fm0version: (_fm0readmarkers, _fm0encodeonemarker),
           _fm1version: (_fm1readmarkers, _fm1encodeonemarker)}

def _readmarkerversion(data):
    return _unpack('>B', data[0:1])[0]

@util.nogc
def _readmarkers(data):
    """Read and enumerate markers from raw data"""
    diskversion = _readmarkerversion(data)
    off = 1
    if diskversion not in formats:
        msg = _('parsing obsolete marker: unknown version %r') % diskversion
        raise error.UnknownVersion(msg, version=diskversion)
    return diskversion, formats[diskversion][0](data, off)

def encodeheader(version=_fm0version):
    return _pack('>B', version)

def encodemarkers(markers, addheader=False, version=_fm0version):
    # Kept separate from flushmarkers(), it will be reused for
    # markers exchange.
    encodeone = formats[version][1]
    if addheader:
        yield encodeheader(version)
    for marker in markers:
        yield encodeone(marker)


class marker(object):
    """Wrap obsolete marker raw data"""

    def __init__(self, repo, data):
        # the repo argument will be used to create changectx in later version
        self._repo = repo
        self._data = data
        self._decodedmeta = None

    def __hash__(self):
        return hash(self._data)

    def __eq__(self, other):
        if type(other) != type(self):
            return False
        return self._data == other._data

    def precnode(self):
        """Precursor changeset node identifier"""
        return self._data[0]

    def succnodes(self):
        """List of successor changesets node identifiers"""
        return self._data[1]

    def parentnodes(self):
        """Parents of the precursors (None if not recorded)"""
        return self._data[5]

    def metadata(self):
        """Decoded metadata dictionary"""
        return dict(self._data[3])

    def date(self):
        """Creation date as (unixtime, offset)"""
        return self._data[4]

    def flags(self):
        """The flags field of the marker"""
        return self._data[2]

@util.nogc
def _addsuccessors(successors, markers):
    for mark in markers:
        successors.setdefault(mark[0], set()).add(mark)

@util.nogc
def _addprecursors(precursors, markers):
    for mark in markers:
        for suc in mark[1]:
            precursors.setdefault(suc, set()).add(mark)

@util.nogc
def _addchildren(children, markers):
    for mark in markers:
        parents = mark[5]
        if parents is not None:
            for p in parents:
                children.setdefault(p, set()).add(mark)

def _checkinvalidmarkers(markers):
    """search for marker with invalid data and raise error if needed

    Exist as a separated function to allow the evolve extension for a more
    subtle handling.
    """
    for mark in markers:
        if node.nullid in mark[1]:
            raise error.Abort(_('bad obsolescence marker detected: '
                               'invalid successors nullid'))

class obsstore(object):
    """Store obsolete markers

    Markers can be accessed with two mappings:
    - precursors[x] -> set(markers on precursors edges of x)
    - successors[x] -> set(markers on successors edges of x)
    - children[x]   -> set(markers on precursors edges of children(x)
    """

    fields = ('prec', 'succs', 'flag', 'meta', 'date', 'parents')
    # prec:    nodeid, precursor changesets
    # succs:   tuple of nodeid, successor changesets (0-N length)
    # flag:    integer, flag field carrying modifier for the markers (see doc)
    # meta:    binary blob, encoded metadata dictionary
    # date:    (float, int) tuple, date of marker creation
    # parents: (tuple of nodeid) or None, parents of precursors
    #          None is used when no data has been recorded

    def __init__(self, svfs, defaultformat=_fm1version, readonly=False):
        # caches for various obsolescence related cache
        self.caches = {}
        self.svfs = svfs
        self._defaultformat = defaultformat
        self._readonly = readonly

    def __iter__(self):
        return iter(self._all)

    def __len__(self):
        return len(self._all)

    def __nonzero__(self):
        if not self._cached('_all'):
            try:
                return self.svfs.stat('obsstore').st_size > 1
            except OSError as inst:
                if inst.errno != errno.ENOENT:
                    raise
                # just build an empty _all list if no obsstore exists, which
                # avoids further stat() syscalls
                pass
        return bool(self._all)

    __bool__ = __nonzero__

    @property
    def readonly(self):
        """True if marker creation is disabled

        Remove me in the future when obsolete marker is always on."""
        return self._readonly

    def create(self, transaction, prec, succs=(), flag=0, parents=None,
               date=None, metadata=None, ui=None):
        """obsolete: add a new obsolete marker

        * ensuring it is hashable
        * check mandatory metadata
        * encode metadata

        If you are a human writing code creating marker you want to use the
        `createmarkers` function in this module instead.

        return True if a new marker have been added, False if the markers
        already existed (no op).
        """
        if metadata is None:
            metadata = {}
        if date is None:
            if 'date' in metadata:
                # as a courtesy for out-of-tree extensions
                date = util.parsedate(metadata.pop('date'))
            elif ui is not None:
                date = ui.configdate('devel', 'default-date')
                if date is None:
                    date = util.makedate()
            else:
                date = util.makedate()
        if len(prec) != 20:
            raise ValueError(prec)
        for succ in succs:
            if len(succ) != 20:
                raise ValueError(succ)
        if prec in succs:
            raise ValueError(_('in-marker cycle with %s') % node.hex(prec))

        metadata = tuple(sorted(metadata.iteritems()))

        marker = (str(prec), tuple(succs), int(flag), metadata, date, parents)
        return bool(self.add(transaction, [marker]))

    def add(self, transaction, markers):
        """Add new markers to the store

        Take care of filtering duplicate.
        Return the number of new marker."""
        if self._readonly:
            raise error.Abort(_('creating obsolete markers is not enabled on '
                              'this repo'))
        known = set()
        getsuccessors = self.successors.get
        new = []
        for m in markers:
            if m not in getsuccessors(m[0], ()) and m not in known:
                known.add(m)
                new.append(m)
        if new:
            f = self.svfs('obsstore', 'ab')
            try:
                offset = f.tell()
                transaction.add('obsstore', offset)
                # offset == 0: new file - add the version header
                for bytes in encodemarkers(new, offset == 0, self._version):
                    f.write(bytes)
            finally:
                # XXX: f.close() == filecache invalidation == obsstore rebuilt.
                # call 'filecacheentry.refresh()'  here
                f.close()
            self._addmarkers(new)
            # new marker *may* have changed several set. invalidate the cache.
            self.caches.clear()
        # records the number of new markers for the transaction hooks
        previous = int(transaction.hookargs.get('new_obsmarkers', '0'))
        transaction.hookargs['new_obsmarkers'] = str(previous + len(new))
        return len(new)

    def mergemarkers(self, transaction, data):
        """merge a binary stream of markers inside the obsstore

        Returns the number of new markers added."""
        version, markers = _readmarkers(data)
        return self.add(transaction, markers)

    @propertycache
    def _data(self):
        return self.svfs.tryread('obsstore')

    @propertycache
    def _version(self):
        if len(self._data) >= 1:
            return _readmarkerversion(self._data)
        else:
            return self._defaultformat

    @propertycache
    def _all(self):
        data = self._data
        if not data:
            return []
        self._version, markers = _readmarkers(data)
        markers = list(markers)
        _checkinvalidmarkers(markers)
        return markers

    @propertycache
    def successors(self):
        successors = {}
        _addsuccessors(successors, self._all)
        return successors

    @propertycache
    def precursors(self):
        precursors = {}
        _addprecursors(precursors, self._all)
        return precursors

    @propertycache
    def children(self):
        children = {}
        _addchildren(children, self._all)
        return children

    def _cached(self, attr):
        return attr in self.__dict__

    def _addmarkers(self, markers):
        markers = list(markers) # to allow repeated iteration
        self._all.extend(markers)
        if self._cached('successors'):
            _addsuccessors(self.successors, markers)
        if self._cached('precursors'):
            _addprecursors(self.precursors, markers)
        if self._cached('children'):
            _addchildren(self.children, markers)
        _checkinvalidmarkers(markers)

    def relevantmarkers(self, nodes):
        """return a set of all obsolescence markers relevant to a set of nodes.

        "relevant" to a set of nodes mean:

        - marker that use this changeset as successor
        - prune marker of direct children on this changeset
        - recursive application of the two rules on precursors of these markers

        It is a set so you cannot rely on order."""

        pendingnodes = set(nodes)
        seenmarkers = set()
        seennodes = set(pendingnodes)
        precursorsmarkers = self.precursors
        succsmarkers = self.successors
        children = self.children
        while pendingnodes:
            direct = set()
            for current in pendingnodes:
                direct.update(precursorsmarkers.get(current, ()))
                pruned = [m for m in children.get(current, ()) if not m[1]]
                direct.update(pruned)
                pruned = [m for m in succsmarkers.get(current, ()) if not m[1]]
                direct.update(pruned)
            direct -= seenmarkers
            pendingnodes = set([m[0] for m in direct])
            seenmarkers |= direct
            pendingnodes -= seennodes
            seennodes |= pendingnodes
        return seenmarkers

def makestore(ui, repo):
    """Create an obsstore instance from a repo."""
    # read default format for new obsstore.
    # developer config: format.obsstore-version
    defaultformat = ui.configint('format', 'obsstore-version', None)
    # rely on obsstore class default when possible.
    kwargs = {}
    if defaultformat is not None:
        kwargs['defaultformat'] = defaultformat
    readonly = not isenabled(repo, createmarkersopt)
    store = obsstore(repo.svfs, readonly=readonly, **kwargs)
    if store and readonly:
        ui.warn(_('obsolete feature not enabled but %i markers found!\n')
                % len(list(store)))
    return store

def _filterprunes(markers):
    """return a set with no prune markers"""
    return set(m for m in markers if m[1])

def exclusivemarkers(repo, nodes):
    """set of markers relevant to "nodes" but no other locally-known nodes

    This function compute the set of markers "exclusive" to a locally-known
    node. This means we walk the markers starting from <nodes> until we reach a
    locally-known precursors outside of <nodes>. Element of <nodes> with
    locally-known successors outside of <nodes> are ignored (since their
    precursors markers are also relevant to these successors).

    For example:

        # (A0 rewritten as A1)
        #
        # A0 <-1- A1 # Marker "1" is exclusive to A1

        or

        # (A0 rewritten as AX; AX rewritten as A1; AX is unkown locally)
        #
        # <-1- A0 <-2- AX <-3- A1 # Marker "2,3" are exclusive to A1

        or

        # (A0 has unknown precursors, A0 rewritten as A1 and A2 (divergence))
        #
        #          <-2- A1 # Marker "2" is exclusive to A0,A1
        #        /
        # <-1- A0
        #        \
        #         <-3- A2 # Marker "3" is exclusive to A0,A2
        #
        # in addition:
        #
        #  Markers "2,3" are exclusive to A1,A2
        #  Markers "1,2,3" are exclusive to A0,A1,A2

        See test/test-obsolete-bundle-strip.t for more examples.

    An example usage is strip. When stripping a changeset, we also want to
    strip the markers exclusive to this changeset. Otherwise we would have
    "dangling"" obsolescence markers from its precursors: Obsolescence markers
    marking a node as obsolete without any successors available locally.

    As for relevant markers, the prune markers for children will be followed.
    Of course, they will only be followed if the pruned children is
    locally-known. Since the prune markers are relevant to the pruned node.
    However, while prune markers are considered relevant to the parent of the
    pruned changesets, prune markers for locally-known changeset (with no
    successors) are considered exclusive to the pruned nodes. This allows
    to strip the prune markers (with the rest of the exclusive chain) alongside
    the pruned changesets.
    """
    # running on a filtered repository would be dangerous as markers could be
    # reported as exclusive when they are relevant for other filtered nodes.
    unfi = repo.unfiltered()

    # shortcut to various useful item
    nm = unfi.changelog.nodemap
    precursorsmarkers = unfi.obsstore.precursors
    successormarkers = unfi.obsstore.successors
    childrenmarkers = unfi.obsstore.children

    # exclusive markers (return of the function)
    exclmarkers = set()
    # we need fast membership testing
    nodes = set(nodes)
    # looking for head in the obshistory
    #
    # XXX we are ignoring all issues in regard with cycle for now.
    stack = [n for n in nodes if not _filterprunes(successormarkers.get(n, ()))]
    stack.sort()
    # nodes already stacked
    seennodes = set(stack)
    while stack:
        current = stack.pop()
        # fetch precursors markers
        markers = list(precursorsmarkers.get(current, ()))
        # extend the list with prune markers
        for mark in successormarkers.get(current, ()):
            if not mark[1]:
                markers.append(mark)
        # and markers from children (looking for prune)
        for mark in childrenmarkers.get(current, ()):
            if not mark[1]:
                markers.append(mark)
        # traverse the markers
        for mark in markers:
            if mark in exclmarkers:
                # markers already selected
                continue

            # If the markers is about the current node, select it
            #
            # (this delay the addition of markers from children)
            if mark[1] or mark[0] == current:
                exclmarkers.add(mark)

            # should we keep traversing through the precursors?
            prec = mark[0]

            # nodes in the stack or already processed
            if prec in seennodes:
                continue

            # is this a locally known node ?
            known = prec in nm
            # if locally-known and not in the <nodes> set the traversal
            # stop here.
            if known and prec not in nodes:
                continue

            # do not keep going if there are unselected markers pointing to this
            # nodes. If we end up traversing these unselected markers later the
            # node will be taken care of at that point.
            precmarkers = _filterprunes(successormarkers.get(prec))
            if precmarkers.issubset(exclmarkers):
                seennodes.add(prec)
                stack.append(prec)

    return exclmarkers

def commonversion(versions):
    """Return the newest version listed in both versions and our local formats.

    Returns None if no common version exists.
    """
    versions.sort(reverse=True)
    # search for highest version known on both side
    for v in versions:
        if v in formats:
            return v
    return None

# arbitrary picked to fit into 8K limit from HTTP server
# you have to take in account:
# - the version header
# - the base85 encoding
_maxpayload = 5300

def _pushkeyescape(markers):
    """encode markers into a dict suitable for pushkey exchange

    - binary data is base85 encoded
    - split in chunks smaller than 5300 bytes"""
    keys = {}
    parts = []
    currentlen = _maxpayload * 2  # ensure we create a new part
    for marker in markers:
        nextdata = _fm0encodeonemarker(marker)
        if (len(nextdata) + currentlen > _maxpayload):
            currentpart = []
            currentlen = 0
            parts.append(currentpart)
        currentpart.append(nextdata)
        currentlen += len(nextdata)
    for idx, part in enumerate(reversed(parts)):
        data = ''.join([_pack('>B', _fm0version)] + part)
        keys['dump%i' % idx] = util.b85encode(data)
    return keys

def listmarkers(repo):
    """List markers over pushkey"""
    if not repo.obsstore:
        return {}
    return _pushkeyescape(sorted(repo.obsstore))

def pushmarker(repo, key, old, new):
    """Push markers over pushkey"""
    if not key.startswith('dump'):
        repo.ui.warn(_('unknown key: %r') % key)
        return 0
    if old:
        repo.ui.warn(_('unexpected old value for %r') % key)
        return 0
    data = util.b85decode(new)
    lock = repo.lock()
    try:
        tr = repo.transaction('pushkey: obsolete markers')
        try:
            repo.obsstore.mergemarkers(tr, data)
            repo.invalidatevolatilesets()
            tr.close()
            return 1
        finally:
            tr.release()
    finally:
        lock.release()

def getmarkers(repo, nodes=None, exclusive=False):
    """returns markers known in a repository

    If <nodes> is specified, only markers "relevant" to those nodes are are
    returned"""
    if nodes is None:
        rawmarkers = repo.obsstore
    elif exclusive:
        rawmarkers = exclusivemarkers(repo, nodes)
    else:
        rawmarkers = repo.obsstore.relevantmarkers(nodes)

    for markerdata in rawmarkers:
        yield marker(repo, markerdata)

def relevantmarkers(repo, node):
    """all obsolete markers relevant to some revision"""
    for markerdata in repo.obsstore.relevantmarkers(node):
        yield marker(repo, markerdata)


def precursormarkers(ctx):
    """obsolete marker marking this changeset as a successors"""
    for data in ctx.repo().obsstore.precursors.get(ctx.node(), ()):
        yield marker(ctx.repo(), data)

def successormarkers(ctx):
    """obsolete marker making this changeset obsolete"""
    for data in ctx.repo().obsstore.successors.get(ctx.node(), ()):
        yield marker(ctx.repo(), data)

def allsuccessors(obsstore, nodes, ignoreflags=0):
    """Yield node for every successor of <nodes>.

    Some successors may be unknown locally.

    This is a linear yield unsuited to detecting split changesets. It includes
    initial nodes too."""
    remaining = set(nodes)
    seen = set(remaining)
    while remaining:
        current = remaining.pop()
        yield current
        for mark in obsstore.successors.get(current, ()):
            # ignore marker flagged with specified flag
            if mark[2] & ignoreflags:
                continue
            for suc in mark[1]:
                if suc not in seen:
                    seen.add(suc)
                    remaining.add(suc)

def allprecursors(obsstore, nodes, ignoreflags=0):
    """Yield node for every precursors of <nodes>.

    Some precursors may be unknown locally.

    This is a linear yield unsuited to detecting folded changesets. It includes
    initial nodes too."""

    remaining = set(nodes)
    seen = set(remaining)
    while remaining:
        current = remaining.pop()
        yield current
        for mark in obsstore.precursors.get(current, ()):
            # ignore marker flagged with specified flag
            if mark[2] & ignoreflags:
                continue
            suc = mark[0]
            if suc not in seen:
                seen.add(suc)
                remaining.add(suc)

def foreground(repo, nodes):
    """return all nodes in the "foreground" of other node

    The foreground of a revision is anything reachable using parent -> children
    or precursor -> successor relation. It is very similar to "descendant" but
    augmented with obsolescence information.

    Beware that possible obsolescence cycle may result if complex situation.
    """
    repo = repo.unfiltered()
    foreground = set(repo.set('%ln::', nodes))
    if repo.obsstore:
        # We only need this complicated logic if there is obsolescence
        # XXX will probably deserve an optimised revset.
        nm = repo.changelog.nodemap
        plen = -1
        # compute the whole set of successors or descendants
        while len(foreground) != plen:
            plen = len(foreground)
            succs = set(c.node() for c in foreground)
            mutable = [c.node() for c in foreground if c.mutable()]
            succs.update(allsuccessors(repo.obsstore, mutable))
            known = (n for n in succs if n in nm)
            foreground = set(repo.set('%ln::', known))
    return set(c.node() for c in foreground)


def successorssets(repo, initialnode, cache=None):
    """Return set of all latest successors of initial nodes

    The successors set of a changeset A are the group of revisions that succeed
    A. It succeeds A as a consistent whole, each revision being only a partial
    replacement. The successors set contains non-obsolete changesets only.

    This function returns the full list of successor sets which is why it
    returns a list of tuples and not just a single tuple. Each tuple is a valid
    successors set. Note that (A,) may be a valid successors set for changeset A
    (see below).

    In most cases, a changeset A will have a single element (e.g. the changeset
    A is replaced by A') in its successors set. Though, it is also common for a
    changeset A to have no elements in its successor set (e.g. the changeset
    has been pruned). Therefore, the returned list of successors sets will be
    [(A',)] or [], respectively.

    When a changeset A is split into A' and B', however, it will result in a
    successors set containing more than a single element, i.e. [(A',B')].
    Divergent changesets will result in multiple successors sets, i.e. [(A',),
    (A'')].

    If a changeset A is not obsolete, then it will conceptually have no
    successors set. To distinguish this from a pruned changeset, the successor
    set will contain itself only, i.e. [(A,)].

    Finally, successors unknown locally are considered to be pruned (obsoleted
    without any successors).

    The optional `cache` parameter is a dictionary that may contain precomputed
    successors sets. It is meant to reuse the computation of a previous call to
    `successorssets` when multiple calls are made at the same time. The cache
    dictionary is updated in place. The caller is responsible for its life
    span. Code that makes multiple calls to `successorssets` *must* use this
    cache mechanism or suffer terrible performance.
    """

    succmarkers = repo.obsstore.successors

    # Stack of nodes we search successors sets for
    toproceed = [initialnode]
    # set version of above list for fast loop detection
    # element added to "toproceed" must be added here
    stackedset = set(toproceed)
    if cache is None:
        cache = {}

    # This while loop is the flattened version of a recursive search for
    # successors sets
    #
    # def successorssets(x):
    #    successors = directsuccessors(x)
    #    ss = [[]]
    #    for succ in directsuccessors(x):
    #        # product as in itertools cartesian product
    #        ss = product(ss, successorssets(succ))
    #    return ss
    #
    # But we can not use plain recursive calls here:
    # - that would blow the python call stack
    # - obsolescence markers may have cycles, we need to handle them.
    #
    # The `toproceed` list act as our call stack. Every node we search
    # successors set for are stacked there.
    #
    # The `stackedset` is set version of this stack used to check if a node is
    # already stacked. This check is used to detect cycles and prevent infinite
    # loop.
    #
    # successors set of all nodes are stored in the `cache` dictionary.
    #
    # After this while loop ends we use the cache to return the successors sets
    # for the node requested by the caller.
    while toproceed:
        # Every iteration tries to compute the successors sets of the topmost
        # node of the stack: CURRENT.
        #
        # There are four possible outcomes:
        #
        # 1) We already know the successors sets of CURRENT:
        #    -> mission accomplished, pop it from the stack.
        # 2) Node is not obsolete:
        #    -> the node is its own successors sets. Add it to the cache.
        # 3) We do not know successors set of direct successors of CURRENT:
        #    -> We add those successors to the stack.
        # 4) We know successors sets of all direct successors of CURRENT:
        #    -> We can compute CURRENT successors set and add it to the
        #       cache.
        #
        current = toproceed[-1]
        if current in cache:
            # case (1): We already know the successors sets
            stackedset.remove(toproceed.pop())
        elif current not in succmarkers:
            # case (2): The node is not obsolete.
            if current in repo:
                # We have a valid last successors.
                cache[current] = [(current,)]
            else:
                # Final obsolete version is unknown locally.
                # Do not count that as a valid successors
                cache[current] = []
        else:
            # cases (3) and (4)
            #
            # We proceed in two phases. Phase 1 aims to distinguish case (3)
            # from case (4):
            #
            #     For each direct successors of CURRENT, we check whether its
            #     successors sets are known. If they are not, we stack the
            #     unknown node and proceed to the next iteration of the while
            #     loop. (case 3)
            #
            #     During this step, we may detect obsolescence cycles: a node
            #     with unknown successors sets but already in the call stack.
            #     In such a situation, we arbitrary set the successors sets of
            #     the node to nothing (node pruned) to break the cycle.
            #
            #     If no break was encountered we proceed to phase 2.
            #
            # Phase 2 computes successors sets of CURRENT (case 4); see details
            # in phase 2 itself.
            #
            # Note the two levels of iteration in each phase.
            # - The first one handles obsolescence markers using CURRENT as
            #   precursor (successors markers of CURRENT).
            #
            #   Having multiple entry here means divergence.
            #
            # - The second one handles successors defined in each marker.
            #
            #   Having none means pruned node, multiple successors means split,
            #   single successors are standard replacement.
            #
            for mark in sorted(succmarkers[current]):
                for suc in mark[1]:
                    if suc not in cache:
                        if suc in stackedset:
                            # cycle breaking
                            cache[suc] = []
                        else:
                            # case (3) If we have not computed successors sets
                            # of one of those successors we add it to the
                            # `toproceed` stack and stop all work for this
                            # iteration.
                            toproceed.append(suc)
                            stackedset.add(suc)
                            break
                else:
                    continue
                break
            else:
                # case (4): we know all successors sets of all direct
                # successors
                #
                # Successors set contributed by each marker depends on the
                # successors sets of all its "successors" node.
                #
                # Each different marker is a divergence in the obsolescence
                # history. It contributes successors sets distinct from other
                # markers.
                #
                # Within a marker, a successor may have divergent successors
                # sets. In such a case, the marker will contribute multiple
                # divergent successors sets. If multiple successors have
                # divergent successors sets, a Cartesian product is used.
                #
                # At the end we post-process successors sets to remove
                # duplicated entry and successors set that are strict subset of
                # another one.
                succssets = []
                for mark in sorted(succmarkers[current]):
                    # successors sets contributed by this marker
                    markss = [[]]
                    for suc in mark[1]:
                        # cardinal product with previous successors
                        productresult = []
                        for prefix in markss:
                            for suffix in cache[suc]:
                                newss = list(prefix)
                                for part in suffix:
                                    # do not duplicated entry in successors set
                                    # first entry wins.
                                    if part not in newss:
                                        newss.append(part)
                                productresult.append(newss)
                        markss = productresult
                    succssets.extend(markss)
                # remove duplicated and subset
                seen = []
                final = []
                candidate = sorted(((set(s), s) for s in succssets if s),
                                   key=lambda x: len(x[1]), reverse=True)
                for setversion, listversion in candidate:
                    for seenset in seen:
                        if setversion.issubset(seenset):
                            break
                    else:
                        final.append(listversion)
                        seen.append(setversion)
                final.reverse() # put small successors set first
                cache[current] = final
    return cache[initialnode]

# mapping of 'set-name' -> <function to compute this set>
cachefuncs = {}
def cachefor(name):
    """Decorator to register a function as computing the cache for a set"""
    def decorator(func):
        assert name not in cachefuncs
        cachefuncs[name] = func
        return func
    return decorator

def getrevs(repo, name):
    """Return the set of revision that belong to the <name> set

    Such access may compute the set and cache it for future use"""
    repo = repo.unfiltered()
    if not repo.obsstore:
        return frozenset()
    if name not in repo.obsstore.caches:
        repo.obsstore.caches[name] = cachefuncs[name](repo)
    return repo.obsstore.caches[name]

# To be simple we need to invalidate obsolescence cache when:
#
# - new changeset is added:
# - public phase is changed
# - obsolescence marker are added
# - strip is used a repo
def clearobscaches(repo):
    """Remove all obsolescence related cache from a repo

    This remove all cache in obsstore is the obsstore already exist on the
    repo.

    (We could be smarter here given the exact event that trigger the cache
    clearing)"""
    # only clear cache is there is obsstore data in this repo
    if 'obsstore' in repo._filecache:
        repo.obsstore.caches.clear()

@cachefor('obsolete')
def _computeobsoleteset(repo):
    """the set of obsolete revisions"""
    getnode = repo.changelog.node
    notpublic = repo._phasecache.getrevset(repo, (phases.draft, phases.secret))
    isobs = repo.obsstore.successors.__contains__
    obs = set(r for r in notpublic if isobs(getnode(r)))
    return obs

@cachefor('unstable')
def _computeunstableset(repo):
    """the set of non obsolete revisions with obsolete parents"""
    revs = [(ctx.rev(), ctx) for ctx in
            repo.set('(not public()) and (not obsolete())')]
    revs.sort(key=lambda x:x[0])
    unstable = set()
    for rev, ctx in revs:
        # A rev is unstable if one of its parent is obsolete or unstable
        # this works since we traverse following growing rev order
        if any((x.obsolete() or (x.rev() in unstable))
                for x in ctx.parents()):
            unstable.add(rev)
    return unstable

@cachefor('suspended')
def _computesuspendedset(repo):
    """the set of obsolete parents with non obsolete descendants"""
    suspended = repo.changelog.ancestors(getrevs(repo, 'unstable'))
    return set(r for r in getrevs(repo, 'obsolete') if r in suspended)

@cachefor('extinct')
def _computeextinctset(repo):
    """the set of obsolete parents without non obsolete descendants"""
    return getrevs(repo, 'obsolete') - getrevs(repo, 'suspended')


@cachefor('bumped')
def _computebumpedset(repo):
    """the set of revs trying to obsolete public revisions"""
    bumped = set()
    # util function (avoid attribute lookup in the loop)
    phase = repo._phasecache.phase # would be faster to grab the full list
    public = phases.public
    cl = repo.changelog
    torev = cl.nodemap.get
    for ctx in repo.set('(not public()) and (not obsolete())'):
        rev = ctx.rev()
        # We only evaluate mutable, non-obsolete revision
        node = ctx.node()
        # (future) A cache of precursors may worth if split is very common
        for pnode in allprecursors(repo.obsstore, [node],
                                   ignoreflags=bumpedfix):
            prev = torev(pnode) # unfiltered! but so is phasecache
            if (prev is not None) and (phase(repo, prev) <= public):
                # we have a public precursor
                bumped.add(rev)
                break # Next draft!
    return bumped

@cachefor('divergent')
def _computedivergentset(repo):
    """the set of rev that compete to be the final successors of some revision.
    """
    divergent = set()
    obsstore = repo.obsstore
    newermap = {}
    for ctx in repo.set('(not public()) - obsolete()'):
        mark = obsstore.precursors.get(ctx.node(), ())
        toprocess = set(mark)
        seen = set()
        while toprocess:
            prec = toprocess.pop()[0]
            if prec in seen:
                continue # emergency cycle hanging prevention
            seen.add(prec)
            if prec not in newermap:
                successorssets(repo, prec, newermap)
            newer = [n for n in newermap[prec] if n]
            if len(newer) > 1:
                divergent.add(ctx.rev())
                break
            toprocess.update(obsstore.precursors.get(prec, ()))
    return divergent


def createmarkers(repo, relations, flag=0, date=None, metadata=None,
                  operation=None):
    """Add obsolete markers between changesets in a repo

    <relations> must be an iterable of (<old>, (<new>, ...)[,{metadata}])
    tuple. `old` and `news` are changectx. metadata is an optional dictionary
    containing metadata for this marker only. It is merged with the global
    metadata specified through the `metadata` argument of this function,

    Trying to obsolete a public changeset will raise an exception.

    Current user and date are used except if specified otherwise in the
    metadata attribute.

    This function operates within a transaction of its own, but does
    not take any lock on the repo.
    """
    # prepare metadata
    if metadata is None:
        metadata = {}
    if 'user' not in metadata:
        metadata['user'] = repo.ui.username()
    useoperation = repo.ui.configbool('experimental',
                                      'evolution.track-operation',
                                      False)
    if useoperation and operation:
        metadata['operation'] = operation
    tr = repo.transaction('add-obsolescence-marker')
    try:
        markerargs = []
        for rel in relations:
            prec = rel[0]
            sucs = rel[1]
            localmetadata = metadata.copy()
            if 2 < len(rel):
                localmetadata.update(rel[2])

            if not prec.mutable():
                raise error.Abort(_("cannot obsolete public changeset: %s")
                                 % prec,
                                 hint="see 'hg help phases' for details")
            nprec = prec.node()
            nsucs = tuple(s.node() for s in sucs)
            npare = None
            if not nsucs:
                npare = tuple(p.node() for p in prec.parents())
            if nprec in nsucs:
                raise error.Abort(_("changeset %s cannot obsolete itself")
                                  % prec)

            # Creating the marker causes the hidden cache to become invalid,
            # which causes recomputation when we ask for prec.parents() above.
            # Resulting in n^2 behavior.  So let's prepare all of the args
            # first, then create the markers.
            markerargs.append((nprec, nsucs, npare, localmetadata))

        for args in markerargs:
            nprec, nsucs, npare, localmetadata = args
            repo.obsstore.create(tr, nprec, nsucs, flag, parents=npare,
                                 date=date, metadata=localmetadata,
                                 ui=repo.ui)
            repo.filteredrevcache.clear()
        tr.close()
    finally:
        tr.release()
