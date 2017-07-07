# sparse.py - allow sparse checkouts of the working directory
#
# Copyright 2014 Facebook, Inc.
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

"""allow sparse checkouts of the working directory (EXPERIMENTAL)

(This extension is not yet protected by backwards compatibility
guarantees. Any aspect may break in future releases until this
notice is removed.)

This extension allows the working directory to only consist of a
subset of files for the revision. This allows specific files or
directories to be explicitly included or excluded. Many repository
operations have performance proportional to the number of files in
the working directory. So only realizing a subset of files in the
working directory can improve performance.

Sparse Config Files
-------------------

The set of files that are part of a sparse checkout are defined by
a sparse config file. The file defines 3 things: includes (files to
include in the sparse checkout), excludes (files to exclude from the
sparse checkout), and profiles (links to other config files).

The file format is newline delimited. Empty lines and lines beginning
with ``#`` are ignored.

Lines beginning with ``%include `` denote another sparse config file
to include. e.g. ``%include tests.sparse``. The filename is relative
to the repository root.

The special lines ``[include]`` and ``[exclude]`` denote the section
for includes and excludes that follow, respectively. It is illegal to
have ``[include]`` after ``[exclude]``. If no sections are defined,
entries are assumed to be in the ``[include]`` section.

Non-special lines resemble file patterns to be added to either includes
or excludes. The syntax of these lines is documented by :hg:`help patterns`.
Patterns are interpreted as ``glob:`` by default and match against the
root of the repository.

Exclusion patterns take precedence over inclusion patterns. So even
if a file is explicitly included, an ``[exclude]`` entry can remove it.

For example, say you have a repository with 3 directories, ``frontend/``,
``backend/``, and ``tools/``. ``frontend/`` and ``backend/`` correspond
to different projects and it is uncommon for someone working on one
to need the files for the other. But ``tools/`` contains files shared
between both projects. Your sparse config files may resemble::

  # frontend.sparse
  frontend/**
  tools/**

  # backend.sparse
  backend/**
  tools/**

Say the backend grows in size. Or there's a directory with thousands
of files you wish to exclude. You can modify the profile to exclude
certain files::

  [include]
  backend/**
  tools/**

  [exclude]
  tools/tests/**
"""

from __future__ import absolute_import

import collections

from mercurial.i18n import _
from mercurial.node import nullid
from mercurial import (
    cmdutil,
    commands,
    context,
    dirstate,
    error,
    extensions,
    hg,
    localrepo,
    match as matchmod,
    merge as mergemod,
    registrar,
    sparse,
    util,
)

# Note for extension authors: ONLY specify testedwith = 'ships-with-hg-core' for
# extensions which SHIP WITH MERCURIAL. Non-mainline extensions should
# be specifying the version(s) of Mercurial they are tested with, or
# leave the attribute unspecified.
testedwith = 'ships-with-hg-core'

cmdtable = {}
command = registrar.command(cmdtable)

def uisetup(ui):
    _setupupdates(ui)
    _setupcommit(ui)

def extsetup(ui):
    sparse.enabled = True

    _setupclone(ui)
    _setuplog(ui)
    _setupadd(ui)
    _setupdirstate(ui)

def reposetup(ui, repo):
    if not util.safehasattr(repo, 'dirstate'):
        return

    _wraprepo(ui, repo)

def replacefilecache(cls, propname, replacement):
    """Replace a filecache property with a new class. This allows changing the
    cache invalidation condition."""
    origcls = cls
    assert callable(replacement)
    while cls is not object:
        if propname in cls.__dict__:
            orig = cls.__dict__[propname]
            setattr(cls, propname, replacement(orig))
            break
        cls = cls.__bases__[0]

    if cls is object:
        raise AttributeError(_("type '%s' has no property '%s'") % (origcls,
                             propname))

def _setupupdates(ui):
    def _calculateupdates(orig, repo, wctx, mctx, ancestors, branchmerge, *arg,
                          **kwargs):
        """Filter updates to only lay out files that match the sparse rules.
        """
        actions, diverge, renamedelete = orig(repo, wctx, mctx, ancestors,
                                              branchmerge, *arg, **kwargs)

        oldrevs = [pctx.rev() for pctx in wctx.parents()]
        oldsparsematch = sparse.matcher(repo, oldrevs)

        if oldsparsematch.always():
            return actions, diverge, renamedelete

        files = set()
        prunedactions = {}

        if branchmerge:
            # If we're merging, use the wctx filter, since we're merging into
            # the wctx.
            sparsematch = sparse.matcher(repo, [wctx.parents()[0].rev()])
        else:
            # If we're updating, use the target context's filter, since we're
            # moving to the target context.
            sparsematch = sparse.matcher(repo, [mctx.rev()])

        temporaryfiles = []
        for file, action in actions.iteritems():
            type, args, msg = action
            files.add(file)
            if sparsematch(file):
                prunedactions[file] = action
            elif type == 'm':
                temporaryfiles.append(file)
                prunedactions[file] = action
            elif branchmerge:
                if type != 'k':
                    temporaryfiles.append(file)
                    prunedactions[file] = action
            elif type == 'f':
                prunedactions[file] = action
            elif file in wctx:
                prunedactions[file] = ('r', args, msg)

        if len(temporaryfiles) > 0:
            ui.status(_("temporarily included %d file(s) in the sparse checkout"
                " for merging\n") % len(temporaryfiles))
            sparse.addtemporaryincludes(repo, temporaryfiles)

            # Add the new files to the working copy so they can be merged, etc
            actions = []
            message = 'temporarily adding to sparse checkout'
            wctxmanifest = repo[None].manifest()
            for file in temporaryfiles:
                if file in wctxmanifest:
                    fctx = repo[None][file]
                    actions.append((file, (fctx.flags(), False), message))

            typeactions = collections.defaultdict(list)
            typeactions['g'] = actions
            mergemod.applyupdates(repo, typeactions, repo[None], repo['.'],
                                  False)

            dirstate = repo.dirstate
            for file, flags, msg in actions:
                dirstate.normal(file)

        profiles = sparse.activeprofiles(repo)
        changedprofiles = profiles & files
        # If an active profile changed during the update, refresh the checkout.
        # Don't do this during a branch merge, since all incoming changes should
        # have been handled by the temporary includes above.
        if changedprofiles and not branchmerge:
            mf = mctx.manifest()
            for file in mf:
                old = oldsparsematch(file)
                new = sparsematch(file)
                if not old and new:
                    flags = mf.flags(file)
                    prunedactions[file] = ('g', (flags, False), '')
                elif old and not new:
                    prunedactions[file] = ('r', [], '')

        return prunedactions, diverge, renamedelete

    extensions.wrapfunction(mergemod, 'calculateupdates', _calculateupdates)

    def _update(orig, repo, node, branchmerge, *args, **kwargs):
        results = orig(repo, node, branchmerge, *args, **kwargs)

        # If we're updating to a location, clean up any stale temporary includes
        # (ex: this happens during hg rebase --abort).
        if not branchmerge and util.safehasattr(repo, 'prunetemporaryincludes'):
            repo.prunetemporaryincludes()
        return results

    extensions.wrapfunction(mergemod, 'update', _update)

def _setupcommit(ui):
    def _refreshoncommit(orig, self, node):
        """Refresh the checkout when commits touch .hgsparse
        """
        orig(self, node)
        repo = self._repo

        ctx = repo[node]
        profiles = sparse.patternsforrev(repo, ctx.rev())[2]

        # profiles will only have data if sparse is enabled.
        if set(profiles) & set(ctx.files()):
            origstatus = repo.status()
            origsparsematch = sparse.matcher(repo)
            _refresh(repo.ui, repo, origstatus, origsparsematch, True)

        if util.safehasattr(repo, 'prunetemporaryincludes'):
            repo.prunetemporaryincludes()

    extensions.wrapfunction(context.committablectx, 'markcommitted',
        _refreshoncommit)

def _setuplog(ui):
    entry = commands.table['^log|history']
    entry[1].append(('', 'sparse', None,
        "limit to changesets affecting the sparse checkout"))

    def _logrevs(orig, repo, opts):
        revs = orig(repo, opts)
        if opts.get('sparse'):
            sparsematch = sparse.matcher(repo)
            def ctxmatch(rev):
                ctx = repo[rev]
                return any(f for f in ctx.files() if sparsematch(f))
            revs = revs.filter(ctxmatch)
        return revs
    extensions.wrapfunction(cmdutil, '_logrevs', _logrevs)

def _clonesparsecmd(orig, ui, repo, *args, **opts):
    include_pat = opts.get('include')
    exclude_pat = opts.get('exclude')
    enableprofile_pat = opts.get('enable_profile')
    include = exclude = enableprofile = False
    if include_pat:
        pat = include_pat
        include = True
    if exclude_pat:
        pat = exclude_pat
        exclude = True
    if enableprofile_pat:
        pat = enableprofile_pat
        enableprofile = True
    if sum([include, exclude, enableprofile]) > 1:
        raise error.Abort(_("too many flags specified."))
    if include or exclude or enableprofile:
        def clonesparse(orig, self, node, overwrite, *args, **kwargs):
            _config(self.ui, self.unfiltered(), pat, {}, include=include,
                    exclude=exclude, enableprofile=enableprofile)
            return orig(self, node, overwrite, *args, **kwargs)
        extensions.wrapfunction(hg, 'updaterepo', clonesparse)
    return orig(ui, repo, *args, **opts)

def _setupclone(ui):
    entry = commands.table['^clone']
    entry[1].append(('', 'enable-profile', [],
                    'enable a sparse profile'))
    entry[1].append(('', 'include', [],
                    'include sparse pattern'))
    entry[1].append(('', 'exclude', [],
                    'exclude sparse pattern'))
    extensions.wrapcommand(commands.table, 'clone', _clonesparsecmd)

def _setupadd(ui):
    entry = commands.table['^add']
    entry[1].append(('s', 'sparse', None,
                    'also include directories of added files in sparse config'))

    def _add(orig, ui, repo, *pats, **opts):
        if opts.get('sparse'):
            dirs = set()
            for pat in pats:
                dirname, basename = util.split(pat)
                dirs.add(dirname)
            _config(ui, repo, list(dirs), opts, include=True)
        return orig(ui, repo, *pats, **opts)

    extensions.wrapcommand(commands.table, 'add', _add)

def _setupdirstate(ui):
    """Modify the dirstate to prevent stat'ing excluded files,
    and to prevent modifications to files outside the checkout.
    """

    def _dirstate(orig, repo):
        dirstate = orig(repo)
        dirstate.repo = repo
        return dirstate
    extensions.wrapfunction(
        localrepo.localrepository.dirstate, 'func', _dirstate)

    # The atrocity below is needed to wrap dirstate._ignore. It is a cached
    # property, which means normal function wrapping doesn't work.
    class ignorewrapper(object):
        def __init__(self, orig):
            self.orig = orig
            self.origignore = None
            self.func = None
            self.sparsematch = None

        def __get__(self, obj, type=None):
            repo = obj.repo
            origignore = self.orig.__get__(obj)

            sparsematch = sparse.matcher(repo)
            if sparsematch.always():
                return origignore

            if self.sparsematch != sparsematch or self.origignore != origignore:
                self.func = matchmod.unionmatcher([
                    origignore, matchmod.negatematcher(sparsematch)])
                self.sparsematch = sparsematch
                self.origignore = origignore
            return self.func

        def __set__(self, obj, value):
            return self.orig.__set__(obj, value)

        def __delete__(self, obj):
            return self.orig.__delete__(obj)

    replacefilecache(dirstate.dirstate, '_ignore', ignorewrapper)

    # dirstate.rebuild should not add non-matching files
    def _rebuild(orig, self, parent, allfiles, changedfiles=None):
        matcher = sparse.matcher(self.repo)
        if not matcher.always():
            allfiles = allfiles.matches(matcher)
            if changedfiles:
                changedfiles = [f for f in changedfiles if matcher(f)]

            if changedfiles is not None:
                # In _rebuild, these files will be deleted from the dirstate
                # when they are not found to be in allfiles
                dirstatefilestoremove = set(f for f in self if not matcher(f))
                changedfiles = dirstatefilestoremove.union(changedfiles)

        return orig(self, parent, allfiles, changedfiles)
    extensions.wrapfunction(dirstate.dirstate, 'rebuild', _rebuild)

    # Prevent adding files that are outside the sparse checkout
    editfuncs = ['normal', 'add', 'normallookup', 'copy', 'remove', 'merge']
    hint = _('include file with `hg debugsparse --include <pattern>` or use ' +
             '`hg add -s <file>` to include file directory while adding')
    for func in editfuncs:
        def _wrapper(orig, self, *args):
            repo = self.repo
            sparsematch = sparse.matcher(repo)
            if not sparsematch.always():
                dirstate = repo.dirstate
                for f in args:
                    if (f is not None and not sparsematch(f) and
                        f not in dirstate):
                        raise error.Abort(_("cannot add '%s' - it is outside "
                                            "the sparse checkout") % f,
                                          hint=hint)
            return orig(self, *args)
        extensions.wrapfunction(dirstate.dirstate, func, _wrapper)

def _wraprepo(ui, repo):
    class SparseRepo(repo.__class__):
        def prunetemporaryincludes(self):
            if repo.vfs.exists('tempsparse'):
                origstatus = self.status()
                modified, added, removed, deleted, a, b, c = origstatus
                if modified or added or removed or deleted:
                    # Still have pending changes. Don't bother trying to prune.
                    return

                sparsematch = sparse.matcher(self, includetemp=False)
                dirstate = self.dirstate
                actions = []
                dropped = []
                tempincludes = sparse.readtemporaryincludes(self)
                for file in tempincludes:
                    if file in dirstate and not sparsematch(file):
                        message = 'dropping temporarily included sparse files'
                        actions.append((file, None, message))
                        dropped.append(file)

                typeactions = collections.defaultdict(list)
                typeactions['r'] = actions
                mergemod.applyupdates(self, typeactions, self[None], self['.'],
                                      False)

                # Fix dirstate
                for file in dropped:
                    dirstate.drop(file)

                self.vfs.unlink('tempsparse')
                sparse.invalidatesignaturecache(self)
                msg = _("cleaned up %d temporarily added file(s) from the "
                        "sparse checkout\n")
                ui.status(msg % len(tempincludes))

    if 'dirstate' in repo._filecache:
        repo.dirstate.repo = repo

    repo.__class__ = SparseRepo

@command('^debugsparse', [
    ('I', 'include', False, _('include files in the sparse checkout')),
    ('X', 'exclude', False, _('exclude files in the sparse checkout')),
    ('d', 'delete', False, _('delete an include/exclude rule')),
    ('f', 'force', False, _('allow changing rules even with pending changes')),
    ('', 'enable-profile', False, _('enables the specified profile')),
    ('', 'disable-profile', False, _('disables the specified profile')),
    ('', 'import-rules', False, _('imports rules from a file')),
    ('', 'clear-rules', False, _('clears local include/exclude rules')),
    ('', 'refresh', False, _('updates the working after sparseness changes')),
    ('', 'reset', False, _('makes the repo full again')),
    ] + commands.templateopts,
    _('[--OPTION] PATTERN...'))
def debugsparse(ui, repo, *pats, **opts):
    """make the current checkout sparse, or edit the existing checkout

    The sparse command is used to make the current checkout sparse.
    This means files that don't meet the sparse condition will not be
    written to disk, or show up in any working copy operations. It does
    not affect files in history in any way.

    Passing no arguments prints the currently applied sparse rules.

    --include and --exclude are used to add and remove files from the sparse
    checkout. The effects of adding an include or exclude rule are applied
    immediately. If applying the new rule would cause a file with pending
    changes to be added or removed, the command will fail. Pass --force to
    force a rule change even with pending changes (the changes on disk will
    be preserved).

    --delete removes an existing include/exclude rule. The effects are
    immediate.

    --refresh refreshes the files on disk based on the sparse rules. This is
    only necessary if .hg/sparse was changed by hand.

    --enable-profile and --disable-profile accept a path to a .hgsparse file.
    This allows defining sparse checkouts and tracking them inside the
    repository. This is useful for defining commonly used sparse checkouts for
    many people to use. As the profile definition changes over time, the sparse
    checkout will automatically be updated appropriately, depending on which
    changeset is checked out. Changes to .hgsparse are not applied until they
    have been committed.

    --import-rules accepts a path to a file containing rules in the .hgsparse
    format, allowing you to add --include, --exclude and --enable-profile rules
    in bulk. Like the --include, --exclude and --enable-profile switches, the
    changes are applied immediately.

    --clear-rules removes all local include and exclude rules, while leaving
    any enabled profiles in place.

    Returns 0 if editing the sparse checkout succeeds.
    """
    include = opts.get('include')
    exclude = opts.get('exclude')
    force = opts.get('force')
    enableprofile = opts.get('enable_profile')
    disableprofile = opts.get('disable_profile')
    importrules = opts.get('import_rules')
    clearrules = opts.get('clear_rules')
    delete = opts.get('delete')
    refresh = opts.get('refresh')
    reset = opts.get('reset')
    count = sum([include, exclude, enableprofile, disableprofile, delete,
                 importrules, refresh, clearrules, reset])
    if count > 1:
        raise error.Abort(_("too many flags specified"))

    if count == 0:
        if repo.vfs.exists('sparse'):
            ui.status(repo.vfs.read("sparse") + "\n")
            temporaryincludes = sparse.readtemporaryincludes(repo)
            if temporaryincludes:
                ui.status(_("Temporarily Included Files (for merge/rebase):\n"))
                ui.status(("\n".join(temporaryincludes) + "\n"))
        else:
            ui.status(_('repo is not sparse\n'))
        return

    if include or exclude or delete or reset or enableprofile or disableprofile:
        _config(ui, repo, pats, opts, include=include, exclude=exclude,
                reset=reset, delete=delete, enableprofile=enableprofile,
                disableprofile=disableprofile, force=force)

    if importrules:
        _import(ui, repo, pats, opts, force=force)

    if clearrules:
        _clear(ui, repo, pats, force=force)

    if refresh:
        try:
            wlock = repo.wlock()
            fcounts = map(
                len,
                _refresh(ui, repo, repo.status(), sparse.matcher(repo), force))
            _verbose_output(ui, opts, 0, 0, 0, *fcounts)
        finally:
            wlock.release()

def _config(ui, repo, pats, opts, include=False, exclude=False, reset=False,
            delete=False, enableprofile=False, disableprofile=False,
            force=False):
    """
    Perform a sparse config update. Only one of the kwargs may be specified.
    """
    wlock = repo.wlock()
    try:
        oldsparsematch = sparse.matcher(repo)

        raw = repo.vfs.tryread('sparse')
        if raw:
            oldinclude, oldexclude, oldprofiles = map(
                set, sparse.parseconfig(ui, raw))
        else:
            oldinclude = set()
            oldexclude = set()
            oldprofiles = set()

        try:
            if reset:
                newinclude = set()
                newexclude = set()
                newprofiles = set()
            else:
                newinclude = set(oldinclude)
                newexclude = set(oldexclude)
                newprofiles = set(oldprofiles)

            oldstatus = repo.status()

            if any(pat.startswith('/') for pat in pats):
                ui.warn(_('warning: paths cannot start with /, ignoring: %s\n')
                          % ([pat for pat in pats if pat.startswith('/')]))
            elif include:
                newinclude.update(pats)
            elif exclude:
                newexclude.update(pats)
            elif enableprofile:
                newprofiles.update(pats)
            elif disableprofile:
                newprofiles.difference_update(pats)
            elif delete:
                newinclude.difference_update(pats)
                newexclude.difference_update(pats)

            sparse.writeconfig(repo, newinclude, newexclude, newprofiles)

            fcounts = map(
                len, _refresh(ui, repo, oldstatus, oldsparsematch, force))

            profilecount = (len(newprofiles - oldprofiles) -
                            len(oldprofiles - newprofiles))
            includecount = (len(newinclude - oldinclude) -
                            len(oldinclude - newinclude))
            excludecount = (len(newexclude - oldexclude) -
                            len(oldexclude - newexclude))
            _verbose_output(
                ui, opts, profilecount, includecount, excludecount, *fcounts)
        except Exception:
            sparse.writeconfig(repo, oldinclude, oldexclude, oldprofiles)
            raise
    finally:
        wlock.release()

def _import(ui, repo, files, opts, force=False):
    with repo.wlock():
        # load union of current active profile
        revs = [repo.changelog.rev(node) for node in
                repo.dirstate.parents() if node != nullid]

        # read current configuration
        raw = repo.vfs.tryread('sparse')
        oincludes, oexcludes, oprofiles = sparse.parseconfig(ui, raw)
        includes, excludes, profiles = map(
                set, (oincludes, oexcludes, oprofiles))

        # all active rules
        aincludes, aexcludes, aprofiles = set(), set(), set()
        for rev in revs:
            rincludes, rexcludes, rprofiles = sparse.patternsforrev(repo, rev)
            aincludes.update(rincludes)
            aexcludes.update(rexcludes)
            aprofiles.update(rprofiles)

        # import rules on top; only take in rules that are not yet
        # part of the active rules.
        changed = False
        for file in files:
            with util.posixfile(util.expandpath(file)) as importfile:
                iincludes, iexcludes, iprofiles = sparse.parseconfig(
                    ui, importfile.read())
                oldsize = len(includes) + len(excludes) + len(profiles)
                includes.update(iincludes - aincludes)
                excludes.update(iexcludes - aexcludes)
                profiles.update(set(iprofiles) - aprofiles)
                if len(includes) + len(excludes) + len(profiles) > oldsize:
                    changed = True

        profilecount = includecount = excludecount = 0
        fcounts = (0, 0, 0)

        if changed:
            profilecount = len(profiles - aprofiles)
            includecount = len(includes - aincludes)
            excludecount = len(excludes - aexcludes)

            oldstatus = repo.status()
            oldsparsematch = sparse.matcher(repo)
            sparse.writeconfig(repo, includes, excludes, profiles)

            try:
                fcounts = map(
                    len, _refresh(ui, repo, oldstatus, oldsparsematch, force))
            except Exception:
                sparse.writeconfig(repo, oincludes, oexcludes, oprofiles)
                raise

        _verbose_output(ui, opts, profilecount, includecount, excludecount,
                        *fcounts)

def _clear(ui, repo, files, force=False):
    with repo.wlock():
        raw = repo.vfs.tryread('sparse')
        includes, excludes, profiles = sparse.parseconfig(ui, raw)

        if includes or excludes:
            oldstatus = repo.status()
            oldsparsematch = sparse.matcher(repo)
            sparse.writeconfig(repo, set(), set(), profiles)
            _refresh(ui, repo, oldstatus, oldsparsematch, force)

def _refresh(ui, repo, origstatus, origsparsematch, force):
    """Refreshes which files are on disk by comparing the old status and
    sparsematch with the new sparsematch.

    Will raise an exception if a file with pending changes is being excluded
    or included (unless force=True).
    """
    modified, added, removed, deleted, unknown, ignored, clean = origstatus

    # Verify there are no pending changes
    pending = set()
    pending.update(modified)
    pending.update(added)
    pending.update(removed)
    sparsematch = sparse.matcher(repo)
    abort = False
    for file in pending:
        if not sparsematch(file):
            ui.warn(_("pending changes to '%s'\n") % file)
            abort = not force
    if abort:
        raise error.Abort(_("could not update sparseness due to " +
            "pending changes"))

    # Calculate actions
    dirstate = repo.dirstate
    ctx = repo['.']
    added = []
    lookup = []
    dropped = []
    mf = ctx.manifest()
    files = set(mf)

    actions = {}

    for file in files:
        old = origsparsematch(file)
        new = sparsematch(file)
        # Add files that are newly included, or that don't exist in
        # the dirstate yet.
        if (new and not old) or (old and new and not file in dirstate):
            fl = mf.flags(file)
            if repo.wvfs.exists(file):
                actions[file] = ('e', (fl,), '')
                lookup.append(file)
            else:
                actions[file] = ('g', (fl, False), '')
                added.append(file)
        # Drop files that are newly excluded, or that still exist in
        # the dirstate.
        elif (old and not new) or (not old and not new and file in dirstate):
            dropped.append(file)
            if file not in pending:
                actions[file] = ('r', [], '')

    # Verify there are no pending changes in newly included files
    abort = False
    for file in lookup:
        ui.warn(_("pending changes to '%s'\n") % file)
        abort = not force
    if abort:
        raise error.Abort(_("cannot change sparseness due to " +
            "pending changes (delete the files or use --force " +
            "to bring them back dirty)"))

    # Check for files that were only in the dirstate.
    for file, state in dirstate.iteritems():
        if not file in files:
            old = origsparsematch(file)
            new = sparsematch(file)
            if old and not new:
                dropped.append(file)

    # Apply changes to disk
    typeactions = dict((m, []) for m in 'a f g am cd dc r dm dg m e k'.split())
    for f, (m, args, msg) in actions.iteritems():
        if m not in typeactions:
            typeactions[m] = []
        typeactions[m].append((f, args, msg))
    mergemod.applyupdates(repo, typeactions, repo[None], repo['.'], False)

    # Fix dirstate
    for file in added:
        dirstate.normal(file)

    for file in dropped:
        dirstate.drop(file)

    for file in lookup:
        # File exists on disk, and we're bringing it back in an unknown state.
        dirstate.normallookup(file)

    return added, dropped, lookup

def _verbose_output(ui, opts, profilecount, includecount, excludecount, added,
                    dropped, lookup):
    """Produce --verbose and templatable output

    This specifically enables -Tjson, providing machine-readable stats on how
    the sparse profile changed.

    """
    with ui.formatter('sparse', opts) as fm:
        fm.startitem()
        fm.condwrite(ui.verbose, 'profiles_added', 'Profile # change: %d\n',
                     profilecount)
        fm.condwrite(ui.verbose, 'include_rules_added',
                     'Include rule # change: %d\n', includecount)
        fm.condwrite(ui.verbose, 'exclude_rules_added',
                     'Exclude rule # change: %d\n', excludecount)
        # In 'plain' verbose mode, mergemod.applyupdates already outputs what
        # files are added or removed outside of the templating formatter
        # framework. No point in repeating ourselves in that case.
        if not fm.isplain():
            fm.condwrite(ui.verbose, 'files_added', 'Files added: %d\n',
                         added)
            fm.condwrite(ui.verbose, 'files_dropped', 'Files dropped: %d\n',
                         dropped)
            fm.condwrite(ui.verbose, 'files_conflicting',
                         'Files conflicting: %d\n', lookup)