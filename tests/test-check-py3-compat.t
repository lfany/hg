#require test-repo

  $ . "$TESTDIR/helpers-testrepo.sh"
  $ cd "$TESTDIR"/..

  $ hg files 'set:(**.py)' | sed 's|\\|/|g' | xargs python contrib/check-py3-compat.py
  hgext/fsmonitor/pywatchman/__init__.py not using absolute_import
  hgext/fsmonitor/pywatchman/__init__.py requires print_function
  hgext/fsmonitor/pywatchman/capabilities.py not using absolute_import
  hgext/fsmonitor/pywatchman/pybser.py not using absolute_import
  i18n/check-translation.py not using absolute_import
  setup.py not using absolute_import
  tests/test-demandimport.py not using absolute_import

#if py3exe
  $ hg files 'set:(**.py) - grep(pygments)' | sed 's|\\|/|g' \
  > | xargs $PYTHON3 contrib/check-py3-compat.py \
  > | sed 's/[0-9][0-9]*)$/*)/'
  doc/hgmanpage.py: invalid syntax: invalid syntax (<unknown>, line *)
  hgext/acl.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/automv.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/blackbox.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/bugzilla.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/censor.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/chgserver.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/children.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/churn.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/clonebundles.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/color.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/convert/bzr.py: error importing module: <SystemError> Parent module 'hgext.convert' not loaded, cannot perform relative import (line *)
  hgext/convert/common.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/convert/convcmd.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/convert/cvs.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/convert/cvsps.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/convert/darcs.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/convert/filemap.py: error importing module: <SystemError> Parent module 'hgext.convert' not loaded, cannot perform relative import (line *)
  hgext/convert/git.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/convert/gnuarch.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/convert/hg.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/convert/monotone.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/convert/p4.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/convert/subversion.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/convert/transport.py: error importing module: <ImportError> No module named 'svn.client' (line *)
  hgext/eol.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/extdiff.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/factotum.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/fetch.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/fsmonitor/state.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/fsmonitor/watchmanclient.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/gpg.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/graphlog.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/hgk.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/histedit.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/journal.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/keyword.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/largefiles/basestore.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/largefiles/lfcommands.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/largefiles/lfutil.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/largefiles/localstore.py: error importing module: <SystemError> Parent module 'hgext.largefiles' not loaded, cannot perform relative import (line *)
  hgext/largefiles/overrides.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/largefiles/proto.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/largefiles/remotestore.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/largefiles/reposetup.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/largefiles/storefactory.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/largefiles/uisetup.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/largefiles/wirestore.py: error importing module: <SystemError> Parent module 'hgext.largefiles' not loaded, cannot perform relative import (line *)
  hgext/mq.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/notify.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/pager.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/patchbomb.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/purge.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/rebase.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/record.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/relink.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/schemes.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/share.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/shelve.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/strip.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/transplant.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  hgext/win32text.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/archival.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/bookmarks.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/branchmap.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/bundle2.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/bundlerepo.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/byterange.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/changegroup.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/changelog.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/cmdutil.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/commands.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/commandserver.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/config.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/context.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/copies.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/crecord.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/destutil.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/dirstate.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/discovery.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/dispatch.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/encoding.py: error importing module: <TypeError> bytes expected, not str (line *)
  mercurial/exchange.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/extensions.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/filelog.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/filemerge.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/fileset.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/formatter.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/graphmod.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/help.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/hg.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/hgweb/common.py: error importing module: <SystemError> Parent module 'mercurial.hgweb' not loaded, cannot perform relative import (line *)
  mercurial/hgweb/hgweb_mod.py: error importing module: <SystemError> Parent module 'mercurial.hgweb' not loaded, cannot perform relative import (line *)
  mercurial/hgweb/hgwebdir_mod.py: error importing module: <SystemError> Parent module 'mercurial.hgweb' not loaded, cannot perform relative import (line *)
  mercurial/hgweb/protocol.py: error importing module: <SystemError> Parent module 'mercurial.hgweb' not loaded, cannot perform relative import (line *)
  mercurial/hgweb/request.py: error importing module: <SystemError> Parent module 'mercurial.hgweb' not loaded, cannot perform relative import (line *)
  mercurial/hgweb/server.py: error importing module: <SystemError> Parent module 'mercurial.hgweb' not loaded, cannot perform relative import (line *)
  mercurial/hgweb/webcommands.py: error importing module: <SystemError> Parent module 'mercurial.hgweb' not loaded, cannot perform relative import (line *)
  mercurial/hgweb/webutil.py: error importing module: <SystemError> Parent module 'mercurial.hgweb' not loaded, cannot perform relative import (line *)
  mercurial/hgweb/wsgicgi.py: error importing module: <SystemError> Parent module 'mercurial.hgweb' not loaded, cannot perform relative import (line *)
  mercurial/hook.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/httpconnection.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/httppeer.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
  mercurial/i18n.py: error importing module: <TypeError> bytes expected, not str (line *)
  mercurial/keepalive.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/localrepo.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/lock.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/mail.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/manifest.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/match.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/mdiff.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/merge.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/minirst.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/namespaces.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/obsolete.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/patch.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/pathutil.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/peer.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/profiling.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/pushkey.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/pvec.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/registrar.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/repair.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/repoview.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/revlog.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/revset.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/scmutil.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/scmwindows.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/similar.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/simplemerge.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/sshpeer.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/sshserver.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/sslutil.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/statichttprepo.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/store.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/streamclone.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/subrepo.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/tagmerge.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/tags.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/templatefilters.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/templatekw.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/templater.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/transaction.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/ui.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/unionrepo.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/url.py: error importing: <TypeError> int() can't convert non-string with explicit base (error at util.py:*)
  mercurial/verify.py: error importing module: <TypeError> unorderable types: str() >= tuple() (line *)
  mercurial/win32.py: error importing module: <ImportError> No module named 'msvcrt' (line *)
  mercurial/windows.py: error importing module: <ImportError> No module named 'msvcrt' (line *)
  mercurial/wireproto.py: error importing module: <TypeError> unorderable types: str() >= tuple() (line *)

#endif

#if py3exe py3pygments
  $ hg files 'set:(**.py) and grep(pygments)' | sed 's|\\|/|g' \
  > | xargs $PYTHON3 contrib/check-py3-compat.py \
  > | sed 's/[0-9][0-9]*)$/*)/'
  hgext/highlight/highlight.py: error importing: <TypeError> Can't mix strings and bytes in path components (error at i18n.py:*)
#endif
