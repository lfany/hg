# transaction.py - simple journaling scheme for mercurial
#
# This transaction scheme is intended to gracefully handle program
# errors and interruptions. More serious failures like system crashes
# can be recovered with an fsck-like tool. As the whole repository is
# effectively log-structured, this should amount to simply truncating
# anything that isn't referenced in the changelog.
#
# Copyright 2005, 2006 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

from i18n import _
import errno
import error, util

version = 1

def active(func):
    def _active(self, *args, **kwds):
        if self.count == 0:
            raise error.Abort(_(
                'cannot use transaction when it is already committed/aborted'))
        return func(self, *args, **kwds)
    return _active

def _playback(journal, report, opener, entries, backupentries, unlink=True):
    for f, o, _ignore in entries:
        if o or not unlink:
            try:
                fp = opener(f, 'a')
                fp.truncate(o)
                fp.close()
            except IOError:
                report(_("failed to truncate %s\n") % f)
                raise
        else:
            try:
                opener.unlink(f)
            except (IOError, OSError), inst:
                if inst.errno != errno.ENOENT:
                    raise

    backupfiles = []
    for f, b, _ignore in backupentries:
        filepath = opener.join(f)
        backuppath = opener.join(b)
        try:
            util.copyfile(backuppath, filepath)
            backupfiles.append(b)
        except IOError:
            report(_("failed to recover %s\n") % f)
            raise

    opener.unlink(journal)
    backuppath = "%s.backupfiles" % journal
    if opener.exists(backuppath):
        opener.unlink(backuppath)
    for f in backupfiles:
        opener.unlink(f)

class transaction(object):
    def __init__(self, report, opener, journal, after=None, createmode=None,
            onclose=None, onabort=None):
        """Begin a new transaction

        Begins a new transaction that allows rolling back writes in the event of
        an exception.

        * `after`: called after the transaction has been committed
        * `createmode`: the mode of the journal file that will be created
        * `onclose`: called as the transaction is closing, but before it is
        closed
        * `onabort`: called as the transaction is aborting, but before any files
        have been truncated
        """
        self.count = 1
        self.usages = 1
        self.report = report
        self.opener = opener
        self.after = after
        self.onclose = onclose
        self.onabort = onabort
        self.entries = []
        self.backupentries = []
        self.map = {}
        self.backupmap = {}
        self.journal = journal
        self._queue = []
        # a dict of arguments to be passed to hooks
        self.hookargs = {}

        self.backupjournal = "%s.backupfiles" % journal
        self.file = opener.open(self.journal, "w")
        self.backupsfile = opener.open(self.backupjournal, 'w')
        self.backupsfile.write('%d\n' % version)
        if createmode is not None:
            opener.chmod(self.journal, createmode & 0666)
            opener.chmod(self.backupjournal, createmode & 0666)

        # hold file generations to be performed on commit
        self._filegenerators = {}
        # hold callbalk to write pending data for hooks
        self._pendingcallback = {}
        # True is any pending data have been written ever
        self._anypending = False
        # holds callback to call when writing the transaction
        self._finalizecallback = {}

    def __del__(self):
        if self.journal:
            self._abort()

    @active
    def startgroup(self):
        self._queue.append(([], []))

    @active
    def endgroup(self):
        q = self._queue.pop()
        self.entries.extend(q[0])
        self.backupentries.extend(q[1])

        offsets = []
        backups = []
        for f, o, _data in q[0]:
            offsets.append((f, o))

        for f, b, _data in q[1]:
            backups.append((f, b))

        d = ''.join(['%s\0%d\n' % (f, o) for f, o in offsets])
        self.file.write(d)
        self.file.flush()

        d = ''.join(['%s\0%s\n' % (f, b) for f, b in backups])
        self.backupsfile.write(d)
        self.backupsfile.flush()

    @active
    def add(self, file, offset, data=None):
        if file in self.map or file in self.backupmap:
            return
        if self._queue:
            self._queue[-1][0].append((file, offset, data))
            return

        self.entries.append((file, offset, data))
        self.map[file] = len(self.entries) - 1
        # add enough data to the journal to do the truncate
        self.file.write("%s\0%d\n" % (file, offset))
        self.file.flush()

    @active
    def addbackup(self, file, hardlink=True, vfs=None):
        """Adds a backup of the file to the transaction

        Calling addbackup() creates a hardlink backup of the specified file
        that is used to recover the file in the event of the transaction
        aborting.

        * `file`: the file path, relative to .hg/store
        * `hardlink`: use a hardlink to quickly create the backup
        """

        if file in self.map or file in self.backupmap:
            return
        backupfile = "%s.backup.%s" % (self.journal, file)
        if vfs is None:
            vfs = self.opener
        if vfs.exists(file):
            filepath = vfs.join(file)
            backuppath = self.opener.join(backupfile)
            util.copyfiles(filepath, backuppath, hardlink=hardlink)
        else:
            self.add(file, 0)
            return

        if self._queue:
            self._queue[-1][1].append((file, backupfile))
            return

        self.backupentries.append((file, backupfile, None))
        self.backupmap[file] = len(self.backupentries) - 1
        self.backupsfile.write("%s\0%s\n" % (file, backupfile))
        self.backupsfile.flush()

    @active
    def addfilegenerator(self, genid, filenames, genfunc, order=0, vfs=None):
        """add a function to generates some files at transaction commit

        The `genfunc` argument is a function capable of generating proper
        content of each entry in the `filename` tuple.

        At transaction close time, `genfunc` will be called with one file
        object argument per entries in `filenames`.

        The transaction itself is responsible for the backup, creation and
        final write of such file.

        The `genid` argument is used to ensure the same set of file is only
        generated once. Call to `addfilegenerator` for a `genid` already
        present will overwrite the old entry.

        The `order` argument may be used to control the order in which multiple
        generator will be executed.
        """
        # For now, we are unable to do proper backup and restore of custom vfs
        # but for bookmarks that are handled outside this mechanism.
        assert vfs is None or filenames == ('bookmarks',)
        self._filegenerators[genid] = (order, filenames, genfunc, vfs)

    def _generatefiles(self):
        # write files registered for generation
        for entry in sorted(self._filegenerators.values()):
            order, filenames, genfunc, vfs = entry
            if vfs is None:
                vfs = self.opener
            files = []
            try:
                for name in filenames:
                    # Some files are already backed up when creating the
                    # localrepo. Until this is properly fixed we disable the
                    # backup for them.
                    if name not in ('phaseroots', 'bookmarks'):
                        self.addbackup(name)
                    files.append(vfs(name, 'w', atomictemp=True))
                genfunc(*files)
            finally:
                for f in files:
                    f.close()

    @active
    def find(self, file):
        if file in self.map:
            return self.entries[self.map[file]]
        if file in self.backupmap:
            return self.backupentries[self.backupmap[file]]
        return None

    @active
    def replace(self, file, offset, data=None):
        '''
        replace can only replace already committed entries
        that are not pending in the queue
        '''

        if file not in self.map:
            raise KeyError(file)
        index = self.map[file]
        self.entries[index] = (file, offset, data)
        self.file.write("%s\0%d\n" % (file, offset))
        self.file.flush()

    @active
    def nest(self):
        self.count += 1
        self.usages += 1
        return self

    def release(self):
        if self.count > 0:
            self.usages -= 1
        # if the transaction scopes are left without being closed, fail
        if self.count > 0 and self.usages == 0:
            self._abort()

    def running(self):
        return self.count > 0

    def addpending(self, category, callback):
        """add a callback to be called when the transaction is pending

        Category is a unique identifier to allow overwriting an old callback
        with a newer callback.
        """
        self._pendingcallback[category] = callback

    @active
    def writepending(self):
        '''write pending file to temporary version

        This is used to allow hooks to view a transaction before commit'''
        categories = sorted(self._pendingcallback)
        for cat in categories:
            # remove callback since the data will have been flushed
            any = self._pendingcallback.pop(cat)()
            self._anypending = self._anypending or any
        return self._anypending

    @active
    def addfinalize(self, category, callback):
        """add a callback to be called when the transaction is closed

        Category is a unique identifier to allow overwriting old callbacks with
        newer callbacks.
        """
        self._finalizecallback[category] = callback

    @active
    def close(self):
        '''commit the transaction'''
        if self.count == 1 and self.onclose is not None:
            self._generatefiles()
            categories = sorted(self._finalizecallback)
            for cat in categories:
                self._finalizecallback[cat]()
            self.onclose()

        self.count -= 1
        if self.count != 0:
            return
        self.file.close()
        self.backupsfile.close()
        self.entries = []
        if self.after:
            self.after()
        if self.opener.isfile(self.journal):
            self.opener.unlink(self.journal)
        if self.opener.isfile(self.backupjournal):
            self.opener.unlink(self.backupjournal)
            for _f, b, _ignore in self.backupentries:
                self.opener.unlink(b)
        self.backupentries = []
        self.journal = None

    @active
    def abort(self):
        '''abort the transaction (generally called on error, or when the
        transaction is not explicitly committed before going out of
        scope)'''
        self._abort()

    def _abort(self):
        self.count = 0
        self.usages = 0
        self.file.close()
        self.backupsfile.close()

        if self.onabort is not None:
            self.onabort()

        try:
            if not self.entries and not self.backupentries:
                if self.journal:
                    self.opener.unlink(self.journal)
                if self.backupjournal:
                    self.opener.unlink(self.backupjournal)
                return

            self.report(_("transaction abort!\n"))

            try:
                _playback(self.journal, self.report, self.opener,
                          self.entries, self.backupentries, False)
                self.report(_("rollback completed\n"))
            except Exception:
                self.report(_("rollback failed - please run hg recover\n"))
        finally:
            self.journal = None


def rollback(opener, file, report):
    """Rolls back the transaction contained in the given file

    Reads the entries in the specified file, and the corresponding
    '*.backupfiles' file, to recover from an incomplete transaction.

    * `file`: a file containing a list of entries, specifying where
    to truncate each file.  The file should contain a list of
    file\0offset pairs, delimited by newlines. The corresponding
    '*.backupfiles' file should contain a list of file\0backupfile
    pairs, delimited by \0.
    """
    entries = []
    backupentries = []

    fp = opener.open(file)
    lines = fp.readlines()
    fp.close()
    for l in lines:
        try:
            f, o = l.split('\0')
            entries.append((f, int(o), None))
        except ValueError:
            report(_("couldn't read journal entry %r!\n") % l)

    backupjournal = "%s.backupfiles" % file
    if opener.exists(backupjournal):
        fp = opener.open(backupjournal)
        lines = fp.readlines()
        if lines:
            ver = lines[0][:-1]
            if ver == str(version):
                for line in lines[1:]:
                    if line:
                        # Shave off the trailing newline
                        line = line[:-1]
                        f, b = line.split('\0')
                        backupentries.append((f, b, None))
            else:
                report(_("journal was created by a newer version of "
                         "Mercurial"))

    _playback(file, report, opener, entries, backupentries)
