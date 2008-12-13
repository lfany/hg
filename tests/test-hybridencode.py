#!/usr/bin/env python

from mercurial import store

enc = store.hybridencode # used for fncache repo format

def show(s):
    print "A = '%s'" % s
    print "B = '%s'" % enc(s)
    print

show('data/aux.bla/bla.aux/prn/PRN/lpt/com3/nul/coma/foo.NUL/normal.c.i')

show('data/AUX/SECOND/X.PRN/FOURTH/FI:FTH/SIXTH/SEVENTH/EIGHTH/NINETH/TENTH/ELEVENTH/LOREMIPSUM.TXT.i')
show('data/enterprise/openesbaddons/contrib-imola/corba-bc/netbeansplugin/wsdlExtension/src/main/java/META-INF/services/org.netbeans.modules.xml.wsdl.bindingsupport.spi.ExtensibilityElementTemplateProvider.i')
show('data/AUX.THE-QUICK-BROWN-FOX-JU:MPS-OVER-THE-LAZY-DOG-THE-QUICK-BROWN-FOX-JUMPS-OVER-THE-LAZY-DOG.TXT.i')
show('data/Project Planning/Resources/AnotherLongDirectoryName/Followedbyanother/AndAnother/AndThenAnExtremelyLongFileName.txt')
show('data/Project.Planning/Resources/AnotherLongDirectoryName/Followedbyanother/AndAnother/AndThenAnExtremelyLongFileName.txt')
