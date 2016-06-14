# Perforce source for convert extension.
#
# Copyright 2009, Frank Kingswood <frank@kingswood-consulting.co.uk>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.
from __future__ import absolute_import

import marshal
import re

from mercurial.i18n import _
from mercurial import (
    error,
    util,
)

from . import common

def loaditer(f):
    "Yield the dictionary objects generated by p4"
    try:
        while True:
            d = marshal.load(f)
            if not d:
                break
            yield d
    except EOFError:
        pass

def decodefilename(filename):
    """Perforce escapes special characters @, #, *, or %
    with %40, %23, %2A, or %25 respectively

    >>> decodefilename('portable-net45%252Bnetcore45%252Bwp8%252BMonoAndroid')
    'portable-net45%2Bnetcore45%2Bwp8%2BMonoAndroid'
    >>> decodefilename('//Depot/Directory/%2525/%2523/%23%40.%2A')
    '//Depot/Directory/%25/%23/#@.*'
    """
    replacements = [('%2A', '*'), ('%23', '#'), ('%40', '@'), ('%25', '%')]
    for k, v in replacements:
        filename = filename.replace(k, v)
    return filename

class p4_source(common.converter_source):
    def __init__(self, ui, path, revs=None):
        # avoid import cycle
        from . import convcmd

        super(p4_source, self).__init__(ui, path, revs=revs)

        if "/" in path and not path.startswith('//'):
            raise common.NoRepo(_('%s does not look like a P4 repository') %
                                path)

        common.checktool('p4', abort=False)

        self.p4changes = {}
        self.heads = {}
        self.changeset = {}
        self.files = {}
        self.copies = {}
        self.tags = {}
        self.lastbranch = {}
        self.parent = {}
        self.encoding = self.ui.config('convert', 'p4.encoding',
                                       default=convcmd.orig_encoding)
        self.depotname = {}           # mapping from local name to depot name
        self.localname = {} # mapping from depot name to local name
        self.re_type = re.compile(
            "([a-z]+)?(text|binary|symlink|apple|resource|unicode|utf\d+)"
            "(\+\w+)?$")
        self.re_keywords = re.compile(
            r"\$(Id|Header|Date|DateTime|Change|File|Revision|Author)"
            r":[^$\n]*\$")
        self.re_keywords_old = re.compile("\$(Id|Header):[^$\n]*\$")

        if revs and len(revs) > 1:
            raise error.Abort(_("p4 source does not support specifying "
                               "multiple revisions"))
        self._parse(ui, path)

    def _parse_view(self, path):
        "Read changes affecting the path"
        cmd = 'p4 -G changes -s submitted %s' % util.shellquote(path)
        stdout = util.popen(cmd, mode='rb')
        for d in loaditer(stdout):
            c = d.get("change", None)
            if c:
                self.p4changes[c] = True

    def _parse(self, ui, path):
        "Prepare list of P4 filenames and revisions to import"
        ui.status(_('reading p4 views\n'))

        # read client spec or view
        if "/" in path:
            self._parse_view(path)
            if path.startswith("//") and path.endswith("/..."):
                views = {path[:-3]:""}
            else:
                views = {"//": ""}
        else:
            cmd = 'p4 -G client -o %s' % util.shellquote(path)
            clientspec = marshal.load(util.popen(cmd, mode='rb'))

            views = {}
            for client in clientspec:
                if client.startswith("View"):
                    sview, cview = clientspec[client].split()
                    self._parse_view(sview)
                    if sview.endswith("...") and cview.endswith("..."):
                        sview = sview[:-3]
                        cview = cview[:-3]
                    cview = cview[2:]
                    cview = cview[cview.find("/") + 1:]
                    views[sview] = cview

        # list of changes that affect our source files
        self.p4changes = self.p4changes.keys()
        self.p4changes.sort(key=int)

        # list with depot pathnames, longest first
        vieworder = views.keys()
        vieworder.sort(key=len, reverse=True)

        # handle revision limiting
        startrev = self.ui.config('convert', 'p4.startrev', default=0)
        self.p4changes = [x for x in self.p4changes
                          if ((not startrev or int(x) >= int(startrev)) and
                              (not self.revs or int(x) <= int(self.revs[0])))]

        # now read the full changelists to get the list of file revisions
        ui.status(_('collecting p4 changelists\n'))
        lastid = None
        for change in self.p4changes:
            cmd = "p4 -G describe -s %s" % change
            stdout = util.popen(cmd, mode='rb')
            d = marshal.load(stdout)
            desc = self.recode(d.get("desc", ""))
            shortdesc = desc.split("\n", 1)[0]
            t = '%s %s' % (d["change"], repr(shortdesc)[1:-1])
            ui.status(util.ellipsis(t, 80) + '\n')

            if lastid:
                parents = [lastid]
            else:
                parents = []

            date = (int(d["time"]), 0)     # timezone not set
            c = common.commit(author=self.recode(d["user"]),
                              date=util.datestr(date, '%Y-%m-%d %H:%M:%S %1%2'),
                              parents=parents, desc=desc, branch=None,
                              extra={"p4": change})

            files = []
            copies = {}
            copiedfiles = []
            i = 0
            while ("depotFile%d" % i) in d and ("rev%d" % i) in d:
                oldname = d["depotFile%d" % i]
                filename = None
                for v in vieworder:
                    if oldname.lower().startswith(v.lower()):
                        filename = decodefilename(views[v] + oldname[len(v):])
                        break
                if filename:
                    files.append((filename, d["rev%d" % i]))
                    self.depotname[filename] = oldname
                    if (d.get("action%d" % i) == "move/add"):
                        copiedfiles.append(filename)
                    self.localname[oldname] = filename
                i += 1

            # Collect information about copied files
            for filename in copiedfiles:
                oldname = self.depotname[filename]

                flcmd = 'p4 -G filelog %s' \
                      % util.shellquote(oldname)
                flstdout = util.popen(flcmd, mode='rb')

                copiedfilename = None
                for d in loaditer(flstdout):
                    copiedoldname = None

                    i = 0
                    while ("change%d" % i) in d:
                        if (d["change%d" % i] == change and
                            d["action%d" % i] == "move/add"):
                            j = 0
                            while ("file%d,%d" % (i, j)) in d:
                                if d["how%d,%d" % (i, j)] == "moved from":
                                    copiedoldname = d["file%d,%d" % (i, j)]
                                    break
                                j += 1
                        i += 1

                    if copiedoldname and copiedoldname in self.localname:
                        copiedfilename = self.localname[copiedoldname]
                        break

                if copiedfilename:
                    copies[filename] = copiedfilename
                else:
                    ui.warn(_("cannot find source for copied file: %s@%s\n")
                            % (filename, change))

            self.changeset[change] = c
            self.files[change] = files
            self.copies[change] = copies
            lastid = change

        if lastid:
            self.heads = [lastid]

    def getheads(self):
        return self.heads

    def getfile(self, name, rev):
        cmd = 'p4 -G print %s' \
            % util.shellquote("%s#%s" % (self.depotname[name], rev))

        lasterror = None
        while True:
            stdout = util.popen(cmd, mode='rb')

            mode = None
            contents = []
            keywords = None

            for d in loaditer(stdout):
                code = d["code"]
                data = d.get("data")

                if code == "error":
                    # if this is the first time error happened
                    # re-attempt getting the file
                    if not lasterror:
                        lasterror = IOError(d["generic"], data)
                        # this will exit inner-most for-loop
                        break
                    else:
                        raise lasterror

                elif code == "stat":
                    action = d.get("action")
                    if action in ["purge", "delete", "move/delete"]:
                        return None, None
                    p4type = self.re_type.match(d["type"])
                    if p4type:
                        mode = ""
                        flags = ((p4type.group(1) or "")
                               + (p4type.group(3) or ""))
                        if "x" in flags:
                            mode = "x"
                        if p4type.group(2) == "symlink":
                            mode = "l"
                        if "ko" in flags:
                            keywords = self.re_keywords_old
                        elif "k" in flags:
                            keywords = self.re_keywords

                elif code == "text" or code == "binary":
                    contents.append(data)

                lasterror = None

            if not lasterror:
                break

        if mode is None:
            return None, None

        contents = ''.join(contents)

        if keywords:
            contents = keywords.sub("$\\1$", contents)
        if mode == "l" and contents.endswith("\n"):
            contents = contents[:-1]

        return contents, mode

    def getchanges(self, rev, full):
        if full:
            raise error.Abort(_("convert from p4 does not support --full"))
        return self.files[rev], self.copies[rev], set()

    def getcommit(self, rev):
        return self.changeset[rev]

    def gettags(self):
        return self.tags

    def getchangedfiles(self, rev, i):
        return sorted([x[0] for x in self.files[rev]])
