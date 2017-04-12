#require test-repo

Enable obsolescence to avoid the warning issue when obsmarker are found

  $ . "$TESTDIR/helpers-testrepo.sh"

Go back in the hg repo

  $ cd $TESTDIR/..

  $ for node in `hg log --rev 'not public() and ::. and not desc("# no-check-commit")' --template '{node|short}\n'`; do
  >    hg export $node | contrib/check-commit > ${TESTTMP}/check-commit.out
  >    if [ $? -ne 0 ]; then
  >        echo "Revision $node does not comply with rules"
  >        echo '------------------------------------------------------'
  >        cat ${TESTTMP}/check-commit.out
  >        echo
  >   fi
  > done


