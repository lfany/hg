
Create a test repository:

  $ hg init repo
  $ cd repo
  $ touch a ; hg add a ; hg ci -ma
  $ touch b ; hg add b ; hg ci -mb
  $ touch c ; hg add c ; hg ci -mc
  $ hg bundle --base 0 --rev tip bundle.hg -v --type v1
  2 changesets found
  uncompressed size of bundle content:
       332 (changelog)
       282 (manifests)
        93  b
        93  c
  $ hg bundle --base 0 --rev tip bundle2.hg -v --type none-v2
  2 changesets found
  uncompressed size of bundle content:
       372 (changelog)
       322 (manifests)
       113  b
       113  c

Terse output:

  $ hg debugbundle bundle.hg
  0e067c57feba1a5694ca4844f05588bb1bf82342
  991a3460af53952d10ec8a295d3d2cc2e5fa9690

Terse output:

  $ hg debugbundle bundle2.hg
  Stream params: {}
  changegroup -- "{'version': '02'}"
      0e067c57feba1a5694ca4844f05588bb1bf82342
      991a3460af53952d10ec8a295d3d2cc2e5fa9690

Verbose output:

  $ hg debugbundle --all bundle.hg
  format: id, p1, p2, cset, delta base, len(delta)
  
  changelog
  0e067c57feba1a5694ca4844f05588bb1bf82342 3903775176ed42b1458a6281db4a0ccf4d9f287a 0000000000000000000000000000000000000000 0e067c57feba1a5694ca4844f05588bb1bf82342 3903775176ed42b1458a6281db4a0ccf4d9f287a 80
  991a3460af53952d10ec8a295d3d2cc2e5fa9690 0e067c57feba1a5694ca4844f05588bb1bf82342 0000000000000000000000000000000000000000 991a3460af53952d10ec8a295d3d2cc2e5fa9690 0e067c57feba1a5694ca4844f05588bb1bf82342 80
  
  manifest
  686dbf0aeca417636fa26a9121c681eabbb15a20 8515d4bfda768e04af4c13a69a72e28c7effbea7 0000000000000000000000000000000000000000 0e067c57feba1a5694ca4844f05588bb1bf82342 8515d4bfda768e04af4c13a69a72e28c7effbea7 55
  ae25a31b30b3490a981e7b96a3238cc69583fda1 686dbf0aeca417636fa26a9121c681eabbb15a20 0000000000000000000000000000000000000000 991a3460af53952d10ec8a295d3d2cc2e5fa9690 686dbf0aeca417636fa26a9121c681eabbb15a20 55
  
  b
  b80de5d138758541c5f05265ad144ab9fa86d1db 0000000000000000000000000000000000000000 0000000000000000000000000000000000000000 0e067c57feba1a5694ca4844f05588bb1bf82342 0000000000000000000000000000000000000000 0
  
  c
  b80de5d138758541c5f05265ad144ab9fa86d1db 0000000000000000000000000000000000000000 0000000000000000000000000000000000000000 991a3460af53952d10ec8a295d3d2cc2e5fa9690 0000000000000000000000000000000000000000 0

  $ hg debugbundle --all bundle2.hg
  Stream params: {}
  changegroup -- "{'version': '02'}"
      format: id, p1, p2, cset, delta base, len(delta)
  
      changelog
      0e067c57feba1a5694ca4844f05588bb1bf82342 3903775176ed42b1458a6281db4a0ccf4d9f287a 0000000000000000000000000000000000000000 0e067c57feba1a5694ca4844f05588bb1bf82342 3903775176ed42b1458a6281db4a0ccf4d9f287a 80
      991a3460af53952d10ec8a295d3d2cc2e5fa9690 0e067c57feba1a5694ca4844f05588bb1bf82342 0000000000000000000000000000000000000000 991a3460af53952d10ec8a295d3d2cc2e5fa9690 0e067c57feba1a5694ca4844f05588bb1bf82342 80
  
      manifest
      686dbf0aeca417636fa26a9121c681eabbb15a20 8515d4bfda768e04af4c13a69a72e28c7effbea7 0000000000000000000000000000000000000000 0e067c57feba1a5694ca4844f05588bb1bf82342 8515d4bfda768e04af4c13a69a72e28c7effbea7 55
      ae25a31b30b3490a981e7b96a3238cc69583fda1 686dbf0aeca417636fa26a9121c681eabbb15a20 0000000000000000000000000000000000000000 991a3460af53952d10ec8a295d3d2cc2e5fa9690 686dbf0aeca417636fa26a9121c681eabbb15a20 55
  
      b
      b80de5d138758541c5f05265ad144ab9fa86d1db 0000000000000000000000000000000000000000 0000000000000000000000000000000000000000 0e067c57feba1a5694ca4844f05588bb1bf82342 0000000000000000000000000000000000000000 0
  
      c
      b80de5d138758541c5f05265ad144ab9fa86d1db 0000000000000000000000000000000000000000 0000000000000000000000000000000000000000 991a3460af53952d10ec8a295d3d2cc2e5fa9690 0000000000000000000000000000000000000000 0

  $ cd ..
