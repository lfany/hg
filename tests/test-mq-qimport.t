  (see 'hg help phases' for details)
  $ $PYTHON ../writelines.py b 5 'a\n' 5 'a\r\n'
  $ $PYTHON ../writelines.py b 2 'a\n' 10 'b\n' 2 'a\r\n'
  $ touch .hg/patches/append_foo
  append_foo__1
  append_bar
  $ rm .hg/patches/append_foo
  popping append_bar
  popping append_foo
  $ hg qdel append_foo
  $ hg qdel -k append_bar
  $ hg qimport -e append_bar
  adding append_bar to series file
  $ hg qdel -k append_bar
  $ hg qimport -e --name this-name-is-better append_bar
  renaming append_bar to this-name-is-better
import patch of bad filename

  $ touch '../ bad.diff'
  $ hg qimport '../ bad.diff'
  abort: patch name cannot begin or end with whitespace
  [255]
  $ touch '.hg/patches/ bad.diff'
  $ hg qimport -e ' bad.diff'
  abort: patch name cannot begin or end with whitespace
  [255]

  $ hg qimport non-existent-file --name ' foo'
  abort: patch name cannot begin or end with whitespace
  [255]
  $ hg qimport non-existent-file --name 'foo '
  abort: patch name cannot begin or end with whitespace
  [255]

check patch name generation for non-alpha-numeric summary line

  $ cd repo

  $ hg qpop -a -q
  patch queue now empty
  $ hg qseries -v
  0 U imported_patch_b_diff
  1 U 0
  2 U this-name-is-better
  3 U url.diff

  $ echo bb >> b
  $ hg commit -m '==++--=='

  $ hg qimport -r tip
  $ hg qseries -v
  0 A 1.diff
  1 U imported_patch_b_diff
  2 U 0
  3 U this-name-is-better
  4 U url.diff

check reserved patch names

  $ hg qpop -qa
  patch queue now empty
  $ echo >> b
  $ hg commit -m 'status'
  $ echo >> b
  $ hg commit -m '.'
  $ echo >> b
  $ hg commit -m 'taken'
  $ mkdir .hg/patches/taken
  $ touch .hg/patches/taken__1
  $ hg qimport -r -3::
  $ hg qap
  1.diff__1
  2.diff
  taken__2

check very long patch name

  $ hg qpop -qa
  patch queue now empty
  $ echo >> b
  $ hg commit -m 'abcdefghi pqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi pqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi pqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi pqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi pqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi pqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
  $ hg qimport -r .
  $ hg qap
  abcdefghi_pqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghi_pqrstuvwxyzabcdefg