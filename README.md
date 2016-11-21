FeedMaker
=========

Utility set of making feeds from websites

Requirements
------------

1. Python3 & modules
  1. bs4
  1. PyRSS2Gen

Usage
-----

1. . \<feedmaker dir\>/bin/setup.sh
    * ex) . $HOME/workspace/FeedMaker/bin/setup.sh
1. cd \<application dir\>/\<sitedir\>/\<feeddir\>
    * ex) cd $HOME/workspace/FeedMakerApplications/naver/navercast.118
1. run.sh

Test
----

1. . \<feedmaker dir\>/bin/setup.sh
	or you can set some environment variables for debugging.
	* export FEED_MAKER_HOME=/Users/terzeron/workspace/fmd
	* export FEED_MAKER_WWW_ADMIN=/Users/terzeron/public_html/fm
	* export FEED_MAKER_WWW_FEEDS=/Users/terzeron/public_html/xml
	* export FEED_MAKER_CWD=/Users/terzeron/workspace/fma
1. cd test
1. make test
