  $ set -e
  $ hg init


committing changes

  $ count=0
  $ echo > a
  $ while test $count -lt 32 ; do
  >     echo 'a' >> a
  >     test $count -eq 0 && hg add
  >     hg ci -m "msg $count" -d "$count 0"
  >     count=`expr $count + 1`
  > done
  adding a


  $ hg log
  changeset:   31:58c80a7c8a40
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:31 1970 +0000
  summary:     msg 31
  
  changeset:   30:ed2d2f24b11c
  user:        test
  date:        Thu Jan 01 00:00:30 1970 +0000
  summary:     msg 30
  
  changeset:   29:b5bd63375ab9
  user:        test
  date:        Thu Jan 01 00:00:29 1970 +0000
  summary:     msg 29
  
  changeset:   28:8e0c2264c8af
  user:        test
  date:        Thu Jan 01 00:00:28 1970 +0000
  summary:     msg 28
  
  changeset:   27:288867a866e9
  user:        test
  date:        Thu Jan 01 00:00:27 1970 +0000
  summary:     msg 27
  
  changeset:   26:3efc6fd51aeb
  user:        test
  date:        Thu Jan 01 00:00:26 1970 +0000
  summary:     msg 26
  
  changeset:   25:02a84173a97a
  user:        test
  date:        Thu Jan 01 00:00:25 1970 +0000
  summary:     msg 25
  
  changeset:   24:10e0acd3809e
  user:        test
  date:        Thu Jan 01 00:00:24 1970 +0000
  summary:     msg 24
  
  changeset:   23:5ec79163bff4
  user:        test
  date:        Thu Jan 01 00:00:23 1970 +0000
  summary:     msg 23
  
  changeset:   22:06c7993750ce
  user:        test
  date:        Thu Jan 01 00:00:22 1970 +0000
  summary:     msg 22
  
  changeset:   21:e5db6aa3fe2a
  user:        test
  date:        Thu Jan 01 00:00:21 1970 +0000
  summary:     msg 21
  
  changeset:   20:7128fb4fdbc9
  user:        test
  date:        Thu Jan 01 00:00:20 1970 +0000
  summary:     msg 20
  
  changeset:   19:52798545b482
  user:        test
  date:        Thu Jan 01 00:00:19 1970 +0000
  summary:     msg 19
  
  changeset:   18:86977a90077e
  user:        test
  date:        Thu Jan 01 00:00:18 1970 +0000
  summary:     msg 18
  
  changeset:   17:03515f4a9080
  user:        test
  date:        Thu Jan 01 00:00:17 1970 +0000
  summary:     msg 17
  
  changeset:   16:a2e6ea4973e9
  user:        test
  date:        Thu Jan 01 00:00:16 1970 +0000
  summary:     msg 16
  
  changeset:   15:e7fa0811edb0
  user:        test
  date:        Thu Jan 01 00:00:15 1970 +0000
  summary:     msg 15
  
  changeset:   14:ce8f0998e922
  user:        test
  date:        Thu Jan 01 00:00:14 1970 +0000
  summary:     msg 14
  
  changeset:   13:9d7d07bc967c
  user:        test
  date:        Thu Jan 01 00:00:13 1970 +0000
  summary:     msg 13
  
  changeset:   12:1941b52820a5
  user:        test
  date:        Thu Jan 01 00:00:12 1970 +0000
  summary:     msg 12
  
  changeset:   11:7b4cd9578619
  user:        test
  date:        Thu Jan 01 00:00:11 1970 +0000
  summary:     msg 11
  
  changeset:   10:7c5eff49a6b6
  user:        test
  date:        Thu Jan 01 00:00:10 1970 +0000
  summary:     msg 10
  
  changeset:   9:eb44510ef29a
  user:        test
  date:        Thu Jan 01 00:00:09 1970 +0000
  summary:     msg 9
  
  changeset:   8:453eb4dba229
  user:        test
  date:        Thu Jan 01 00:00:08 1970 +0000
  summary:     msg 8
  
  changeset:   7:03750880c6b5
  user:        test
  date:        Thu Jan 01 00:00:07 1970 +0000
  summary:     msg 7
  
  changeset:   6:a3d5c6fdf0d3
  user:        test
  date:        Thu Jan 01 00:00:06 1970 +0000
  summary:     msg 6
  
  changeset:   5:7874a09ea728
  user:        test
  date:        Thu Jan 01 00:00:05 1970 +0000
  summary:     msg 5
  
  changeset:   4:9b2ba8336a65
  user:        test
  date:        Thu Jan 01 00:00:04 1970 +0000
  summary:     msg 4
  
  changeset:   3:b53bea5e2fcb
  user:        test
  date:        Thu Jan 01 00:00:03 1970 +0000
  summary:     msg 3
  
  changeset:   2:db07c04beaca
  user:        test
  date:        Thu Jan 01 00:00:02 1970 +0000
  summary:     msg 2
  
  changeset:   1:5cd978ea5149
  user:        test
  date:        Thu Jan 01 00:00:01 1970 +0000
  summary:     msg 1
  
  changeset:   0:b99c7b9c8e11
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     msg 0
  

  $ hg up -C
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved

bisect test

  $ hg bisect -r
  $ hg bisect -b
  $ hg bisect -g 1
  Testing changeset 16:a2e6ea4973e9 (30 changesets remaining, ~4 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -g
  Testing changeset 23:5ec79163bff4 (15 changesets remaining, ~3 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved

skip

  $ hg bisect -s
  Testing changeset 24:10e0acd3809e (15 changesets remaining, ~3 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -g
  Testing changeset 27:288867a866e9 (7 changesets remaining, ~2 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -g
  Testing changeset 29:b5bd63375ab9 (4 changesets remaining, ~2 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -b
  Testing changeset 28:8e0c2264c8af (2 changesets remaining, ~1 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -g
  The first bad revision is:
  changeset:   29:b5bd63375ab9
  user:        test
  date:        Thu Jan 01 00:00:29 1970 +0000
  summary:     msg 29
  


bisect reverse test

  $ hg bisect -r
  $ hg bisect -b null
  $ hg bisect -g tip
  Testing changeset 15:e7fa0811edb0 (32 changesets remaining, ~5 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -g
  Testing changeset 7:03750880c6b5 (16 changesets remaining, ~4 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved

skip

  $ hg bisect -s
  Testing changeset 6:a3d5c6fdf0d3 (16 changesets remaining, ~4 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -g
  Testing changeset 2:db07c04beaca (7 changesets remaining, ~2 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -g
  Testing changeset 0:b99c7b9c8e11 (3 changesets remaining, ~1 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -b
  Testing changeset 1:5cd978ea5149 (2 changesets remaining, ~1 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -g
  The first good revision is:
  changeset:   1:5cd978ea5149
  user:        test
  date:        Thu Jan 01 00:00:01 1970 +0000
  summary:     msg 1
  

  $ hg bisect -r
  $ hg bisect -g tip
  $ hg bisect -b tip || echo error
  abort: starting revisions are not directly related
  error

  $ hg bisect -r
  $ hg bisect -g null
  $ hg bisect -bU tip
  Testing changeset 15:e7fa0811edb0 (32 changesets remaining, ~5 tests)
  $ hg id
  5cd978ea5149


reproduce AssertionError, issue1228 and issue1182

  $ hg bisect -r
  $ hg bisect -b 4
  $ hg bisect -g 0
  Testing changeset 2:db07c04beaca (4 changesets remaining, ~2 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -s
  Testing changeset 1:5cd978ea5149 (4 changesets remaining, ~2 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -s
  Testing changeset 3:b53bea5e2fcb (4 changesets remaining, ~2 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -s
  Due to skipped revisions, the first bad revision could be any of:
  changeset:   1:5cd978ea5149
  user:        test
  date:        Thu Jan 01 00:00:01 1970 +0000
  summary:     msg 1
  
  changeset:   2:db07c04beaca
  user:        test
  date:        Thu Jan 01 00:00:02 1970 +0000
  summary:     msg 2
  
  changeset:   3:b53bea5e2fcb
  user:        test
  date:        Thu Jan 01 00:00:03 1970 +0000
  summary:     msg 3
  
  changeset:   4:9b2ba8336a65
  user:        test
  date:        Thu Jan 01 00:00:04 1970 +0000
  summary:     msg 4
  


reproduce non converging bisect, issue1182

  $ hg bisect -r
  $ hg bisect -g 0
  $ hg bisect -b 2
  Testing changeset 1:5cd978ea5149 (2 changesets remaining, ~1 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -s
  Due to skipped revisions, the first bad revision could be any of:
  changeset:   1:5cd978ea5149
  user:        test
  date:        Thu Jan 01 00:00:01 1970 +0000
  summary:     msg 1
  
  changeset:   2:db07c04beaca
  user:        test
  date:        Thu Jan 01 00:00:02 1970 +0000
  summary:     msg 2
  


test no action

  $ hg bisect -r
  $ hg bisect || echo failure
  abort: cannot bisect (no known good revisions)
  failure


reproduce AssertionError, issue1445

  $ hg bisect -r
  $ hg bisect -b 6
  $ hg bisect -g 0
  Testing changeset 3:b53bea5e2fcb (6 changesets remaining, ~2 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -s
  Testing changeset 2:db07c04beaca (6 changesets remaining, ~2 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -s
  Testing changeset 4:9b2ba8336a65 (6 changesets remaining, ~2 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -s
  Testing changeset 1:5cd978ea5149 (6 changesets remaining, ~2 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -s
  Testing changeset 5:7874a09ea728 (6 changesets remaining, ~2 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect -g
  The first bad revision is:
  changeset:   6:a3d5c6fdf0d3
  user:        test
  date:        Thu Jan 01 00:00:06 1970 +0000
  summary:     msg 6
  

  $ set +e

test invalid command
assuming that the shell returns 127 if command not found ...

  $ hg bisect -r
  $ hg bisect --command 'exit 127'
  abort: failed to execute exit 127


test bisecting command

  $ cat > script.py <<EOF
  > #!/usr/bin/env python
  > import sys
  > from mercurial import ui, hg
  > repo = hg.repository(ui.ui(), '.')
  > if repo['.'].rev() < 6:
  >     sys.exit(1)
  > EOF
  $ chmod +x script.py
  $ hg bisect -r
  $ hg bisect --good tip
  $ hg bisect --bad 0
  Testing changeset 15:e7fa0811edb0 (31 changesets remaining, ~4 tests)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg bisect --command "'`pwd`/script.py' and some parameters"
  Changeset 15:e7fa0811edb0: good
  Changeset 7:03750880c6b5: good
  Changeset 3:b53bea5e2fcb: bad
  Changeset 5:7874a09ea728: bad
  Changeset 6:a3d5c6fdf0d3: good
  The first good revision is:
  changeset:   6:a3d5c6fdf0d3
  user:        test
  date:        Thu Jan 01 00:00:06 1970 +0000
  summary:     msg 6
  
