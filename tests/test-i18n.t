Translations are optional:

  $ "$TESTDIR/hghave" gettext || exit 80

#if no-outer-repo

Test that translations are compiled and installed correctly.

Default encoding in tests is "ascii" and the translation is encoded
using the "replace" error handler:

  $ LANGUAGE=pt_BR hg tip
  abortado: n?o foi encontrado um reposit?rio em '$TESTTMP' (.hg n?o encontrado)!
  [255]

Using a more accomodating encoding:

  $ HGENCODING=UTF-8 LANGUAGE=pt_BR hg tip
  abortado: n\xc3\xa3o foi encontrado um reposit\xc3\xb3rio em '$TESTTMP' (.hg n\xc3\xa3o encontrado)! (esc)
  [255]

Different encoding:

  $ HGENCODING=Latin-1 LANGUAGE=pt_BR hg tip
  abortado: n\xe3o foi encontrado um reposit\xf3rio em '$TESTTMP' (.hg n\xe3o encontrado)! (esc)
  [255]

#endif

Test keyword search in translated help text:

  $ HGENCODING=UTF-8 LANGUAGE=de hg help -k blättern
  Topics:
  
   extensions Benutzung erweiterter Funktionen
  
  Erweiterungen:
  
   pager Verwendet einen externen Pager zum Bl\xc3\xa4ttern in der Ausgabe von Befehlen (esc)

