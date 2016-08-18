# debugcommands.py - command processing for debug* commands
#
# Copyright 2005-2016 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

from __future__ import absolute_import

import os

from .i18n import _
from .node import (
    hex,
)
from . import (
    bundle2,
    changegroup,
    cmdutil,
    commands,
    context,
    dagparser,
    error,
    exchange,
    hg,
    lock as lockmod,
    revlog,
    scmutil,
    simplemerge,
    streamclone,
)

release = lockmod.release

# We reuse the command table from commands because it is easier than
# teaching dispatch about multiple tables.
command = cmdutil.command(commands.table)

@command('debugancestor', [], _('[INDEX] REV1 REV2'), optionalrepo=True)
def debugancestor(ui, repo, *args):
    """find the ancestor revision of two revisions in a given index"""
    if len(args) == 3:
        index, rev1, rev2 = args
        r = revlog.revlog(scmutil.opener(os.getcwd(), audit=False), index)
        lookup = r.lookup
    elif len(args) == 2:
        if not repo:
            raise error.Abort(_('there is no Mercurial repository here '
                                '(.hg not found)'))
        rev1, rev2 = args
        r = repo.changelog
        lookup = repo.lookup
    else:
        raise error.Abort(_('either two or three arguments required'))
    a = r.ancestor(lookup(rev1), lookup(rev2))
    ui.write('%d:%s\n' % (r.rev(a), hex(a)))

@command('debugbuilddag',
    [('m', 'mergeable-file', None, _('add single file mergeable changes')),
    ('o', 'overwritten-file', None, _('add single file all revs overwrite')),
    ('n', 'new-file', None, _('add new file at each rev'))],
    _('[OPTION]... [TEXT]'))
def debugbuilddag(ui, repo, text=None,
                  mergeable_file=False,
                  overwritten_file=False,
                  new_file=False):
    """builds a repo with a given DAG from scratch in the current empty repo

    The description of the DAG is read from stdin if not given on the
    command line.

    Elements:

     - "+n" is a linear run of n nodes based on the current default parent
     - "." is a single node based on the current default parent
     - "$" resets the default parent to null (implied at the start);
           otherwise the default parent is always the last node created
     - "<p" sets the default parent to the backref p
     - "*p" is a fork at parent p, which is a backref
     - "*p1/p2" is a merge of parents p1 and p2, which are backrefs
     - "/p2" is a merge of the preceding node and p2
     - ":tag" defines a local tag for the preceding node
     - "@branch" sets the named branch for subsequent nodes
     - "#...\\n" is a comment up to the end of the line

    Whitespace between the above elements is ignored.

    A backref is either

     - a number n, which references the node curr-n, where curr is the current
       node, or
     - the name of a local tag you placed earlier using ":tag", or
     - empty to denote the default parent.

    All string valued-elements are either strictly alphanumeric, or must
    be enclosed in double quotes ("..."), with "\\" as escape character.
    """

    if text is None:
        ui.status(_("reading DAG from stdin\n"))
        text = ui.fin.read()

    cl = repo.changelog
    if len(cl) > 0:
        raise error.Abort(_('repository is not empty'))

    # determine number of revs in DAG
    total = 0
    for type, data in dagparser.parsedag(text):
        if type == 'n':
            total += 1

    if mergeable_file:
        linesperrev = 2
        # make a file with k lines per rev
        initialmergedlines = [str(i) for i in xrange(0, total * linesperrev)]
        initialmergedlines.append("")

    tags = []

    wlock = lock = tr = None
    try:
        wlock = repo.wlock()
        lock = repo.lock()
        tr = repo.transaction("builddag")

        at = -1
        atbranch = 'default'
        nodeids = []
        id = 0
        ui.progress(_('building'), id, unit=_('revisions'), total=total)
        for type, data in dagparser.parsedag(text):
            if type == 'n':
                ui.note(('node %s\n' % str(data)))
                id, ps = data

                files = []
                fctxs = {}

                p2 = None
                if mergeable_file:
                    fn = "mf"
                    p1 = repo[ps[0]]
                    if len(ps) > 1:
                        p2 = repo[ps[1]]
                        pa = p1.ancestor(p2)
                        base, local, other = [x[fn].data() for x in (pa, p1,
                                                                     p2)]
                        m3 = simplemerge.Merge3Text(base, local, other)
                        ml = [l.strip() for l in m3.merge_lines()]
                        ml.append("")
                    elif at > 0:
                        ml = p1[fn].data().split("\n")
                    else:
                        ml = initialmergedlines
                    ml[id * linesperrev] += " r%i" % id
                    mergedtext = "\n".join(ml)
                    files.append(fn)
                    fctxs[fn] = context.memfilectx(repo, fn, mergedtext)

                if overwritten_file:
                    fn = "of"
                    files.append(fn)
                    fctxs[fn] = context.memfilectx(repo, fn, "r%i\n" % id)

                if new_file:
                    fn = "nf%i" % id
                    files.append(fn)
                    fctxs[fn] = context.memfilectx(repo, fn, "r%i\n" % id)
                    if len(ps) > 1:
                        if not p2:
                            p2 = repo[ps[1]]
                        for fn in p2:
                            if fn.startswith("nf"):
                                files.append(fn)
                                fctxs[fn] = p2[fn]

                def fctxfn(repo, cx, path):
                    return fctxs.get(path)

                if len(ps) == 0 or ps[0] < 0:
                    pars = [None, None]
                elif len(ps) == 1:
                    pars = [nodeids[ps[0]], None]
                else:
                    pars = [nodeids[p] for p in ps]
                cx = context.memctx(repo, pars, "r%i" % id, files, fctxfn,
                                    date=(id, 0),
                                    user="debugbuilddag",
                                    extra={'branch': atbranch})
                nodeid = repo.commitctx(cx)
                nodeids.append(nodeid)
                at = id
            elif type == 'l':
                id, name = data
                ui.note(('tag %s\n' % name))
                tags.append("%s %s\n" % (hex(repo.changelog.node(id)), name))
            elif type == 'a':
                ui.note(('branch %s\n' % data))
                atbranch = data
            ui.progress(_('building'), id, unit=_('revisions'), total=total)
        tr.close()

        if tags:
            repo.vfs.write("localtags", "".join(tags))
    finally:
        ui.progress(_('building'), None)
        release(tr, lock, wlock)

@command('debugbundle',
        [('a', 'all', None, _('show all details')),
         ('', 'spec', None, _('print the bundlespec of the bundle'))],
        _('FILE'),
        norepo=True)
def debugbundle(ui, bundlepath, all=None, spec=None, **opts):
    """lists the contents of a bundle"""
    with hg.openpath(ui, bundlepath) as f:
        if spec:
            spec = exchange.getbundlespec(ui, f)
            ui.write('%s\n' % spec)
            return

        gen = exchange.readbundle(ui, f, bundlepath)
        if isinstance(gen, bundle2.unbundle20):
            return _debugbundle2(ui, gen, all=all, **opts)
        _debugchangegroup(ui, gen, all=all, **opts)

def _debugchangegroup(ui, gen, all=None, indent=0, **opts):
    indent_string = ' ' * indent
    if all:
        ui.write(("%sformat: id, p1, p2, cset, delta base, len(delta)\n")
                 % indent_string)

        def showchunks(named):
            ui.write("\n%s%s\n" % (indent_string, named))
            chain = None
            for chunkdata in iter(lambda: gen.deltachunk(chain), {}):
                node = chunkdata['node']
                p1 = chunkdata['p1']
                p2 = chunkdata['p2']
                cs = chunkdata['cs']
                deltabase = chunkdata['deltabase']
                delta = chunkdata['delta']
                ui.write("%s%s %s %s %s %s %s\n" %
                         (indent_string, hex(node), hex(p1), hex(p2),
                          hex(cs), hex(deltabase), len(delta)))
                chain = node

        chunkdata = gen.changelogheader()
        showchunks("changelog")
        chunkdata = gen.manifestheader()
        showchunks("manifest")
        for chunkdata in iter(gen.filelogheader, {}):
            fname = chunkdata['filename']
            showchunks(fname)
    else:
        if isinstance(gen, bundle2.unbundle20):
            raise error.Abort(_('use debugbundle2 for this file'))
        chunkdata = gen.changelogheader()
        chain = None
        for chunkdata in iter(lambda: gen.deltachunk(chain), {}):
            node = chunkdata['node']
            ui.write("%s%s\n" % (indent_string, hex(node)))
            chain = node

def _debugbundle2(ui, gen, all=None, **opts):
    """lists the contents of a bundle2"""
    if not isinstance(gen, bundle2.unbundle20):
        raise error.Abort(_('not a bundle2 file'))
    ui.write(('Stream params: %s\n' % repr(gen.params)))
    for part in gen.iterparts():
        ui.write('%s -- %r\n' % (part.type, repr(part.params)))
        if part.type == 'changegroup':
            version = part.params.get('version', '01')
            cg = changegroup.getunbundler(version, part, 'UN')
            _debugchangegroup(ui, cg, all=all, indent=4, **opts)

@command('debugcreatestreamclonebundle', [], 'FILE')
def debugcreatestreamclonebundle(ui, repo, fname):
    """create a stream clone bundle file

    Stream bundles are special bundles that are essentially archives of
    revlog files. They are commonly used for cloning very quickly.
    """
    requirements, gen = streamclone.generatebundlev1(repo)
    changegroup.writechunks(ui, gen, fname)

    ui.write(_('bundle requirements: %s\n') % ', '.join(sorted(requirements)))

@command('debugapplystreamclonebundle', [], 'FILE')
def debugapplystreamclonebundle(ui, repo, fname):
    """apply a stream clone bundle file"""
    f = hg.openpath(ui, fname)
    gen = exchange.readbundle(ui, f, fname)
    gen.apply(repo)

@command('debugcheckstate', [], '')
def debugcheckstate(ui, repo):
    """validate the correctness of the current dirstate"""
    parent1, parent2 = repo.dirstate.parents()
    m1 = repo[parent1].manifest()
    m2 = repo[parent2].manifest()
    errors = 0
    for f in repo.dirstate:
        state = repo.dirstate[f]
        if state in "nr" and f not in m1:
            ui.warn(_("%s in state %s, but not in manifest1\n") % (f, state))
            errors += 1
        if state in "a" and f in m1:
            ui.warn(_("%s in state %s, but also in manifest1\n") % (f, state))
            errors += 1
        if state in "m" and f not in m1 and f not in m2:
            ui.warn(_("%s in state %s, but not in either manifest\n") %
                    (f, state))
            errors += 1
    for f in m1:
        state = repo.dirstate[f]
        if state not in "nrm":
            ui.warn(_("%s in manifest1, but listed as state %s") % (f, state))
            errors += 1
    if errors:
        error = _(".hg/dirstate inconsistent with current parent's manifest")
        raise error.Abort(error)

@command('debugcommands', [], _('[COMMAND]'), norepo=True)
def debugcommands(ui, cmd='', *args):
    """list all available commands and options"""
    for cmd, vals in sorted(commands.table.iteritems()):
        cmd = cmd.split('|')[0].strip('^')
        opts = ', '.join([i[1] for i in vals[1]])
        ui.write('%s: %s\n' % (cmd, opts))

@command('debugcomplete',
    [('o', 'options', None, _('show the command options'))],
    _('[-o] CMD'),
    norepo=True)
def debugcomplete(ui, cmd='', **opts):
    """returns the completion list associated with the given command"""

    if opts.get('options'):
        options = []
        otables = [commands.globalopts]
        if cmd:
            aliases, entry = cmdutil.findcmd(cmd, commands.table, False)
            otables.append(entry[1])
        for t in otables:
            for o in t:
                if "(DEPRECATED)" in o[3]:
                    continue
                if o[0]:
                    options.append('-%s' % o[0])
                options.append('--%s' % o[1])
        ui.write("%s\n" % "\n".join(options))
        return

    cmdlist, unused_allcmds = cmdutil.findpossible(cmd, commands.table)
    if ui.verbose:
        cmdlist = [' '.join(c[0]) for c in cmdlist.values()]
    ui.write("%s\n" % "\n".join(sorted(cmdlist)))

@command('debugdag',
    [('t', 'tags', None, _('use tags as labels')),
    ('b', 'branches', None, _('annotate with branch names')),
    ('', 'dots', None, _('use dots for runs')),
    ('s', 'spaces', None, _('separate elements by spaces'))],
    _('[OPTION]... [FILE [REV]...]'),
    optionalrepo=True)
def debugdag(ui, repo, file_=None, *revs, **opts):
    """format the changelog or an index DAG as a concise textual description

    If you pass a revlog index, the revlog's DAG is emitted. If you list
    revision numbers, they get labeled in the output as rN.

    Otherwise, the changelog DAG of the current repo is emitted.
    """
    spaces = opts.get('spaces')
    dots = opts.get('dots')
    if file_:
        rlog = revlog.revlog(scmutil.opener(os.getcwd(), audit=False), file_)
        revs = set((int(r) for r in revs))
        def events():
            for r in rlog:
                yield 'n', (r, list(p for p in rlog.parentrevs(r)
                                        if p != -1))
                if r in revs:
                    yield 'l', (r, "r%i" % r)
    elif repo:
        cl = repo.changelog
        tags = opts.get('tags')
        branches = opts.get('branches')
        if tags:
            labels = {}
            for l, n in repo.tags().items():
                labels.setdefault(cl.rev(n), []).append(l)
        def events():
            b = "default"
            for r in cl:
                if branches:
                    newb = cl.read(cl.node(r))[5]['branch']
                    if newb != b:
                        yield 'a', newb
                        b = newb
                yield 'n', (r, list(p for p in cl.parentrevs(r)
                                        if p != -1))
                if tags:
                    ls = labels.get(r)
                    if ls:
                        for l in ls:
                            yield 'l', (r, l)
    else:
        raise error.Abort(_('need repo for changelog dag'))

    for line in dagparser.dagtextlines(events(),
                                       addspaces=spaces,
                                       wraplabels=True,
                                       wrapannotations=True,
                                       wrapnonlinear=dots,
                                       usedots=dots,
                                       maxlinewidth=70):
        ui.write(line)
        ui.write("\n")
