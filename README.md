FeedMaker
=========

Utility set for making feeds from crawling websites

Requirements
------------

* Python3 & modules
  * bs4, PyRSS2Gen, selenium, ...
  * `pip install -r requirements.txt`
* chromedriver
  * http://chromedriver.chromium.org/downloads
  * You should download chromedriver appropriate for chrome browser installed on your system. And this binary must be located in PATH environment variable.
  * Also you should install chrome browser.
* FeedMaker & FeedMakerApplications
  * https://github.com/terzeron/FeedMaker/archive/master.zip
  * https://github.com/terzeron/FeedMakerApplications/archive/master.zip
  * You would be good to use $HOME/workspace/fm & $HOME/workspace/fma for these projects.
  
Usage
-----

* Apply environment variables
  * `. <feedmaker dir>/bin/setup.sh`
  * ex) `. $HOME/workspace/FeedMaker/bin/setup.sh`
* Change thcurrent working directory to a feed directory
  * `cd <application dir>/<sitedir>/<feeddir>`
  * ex) `cd $HOME/workspace/FeedMakerApplications/naver/navercast.118`
* Run the FeedMaker
  * `run.py`

Test
----

* Apply environment variables 
  * `. <feedmaker dir>/bin/setup.sh`
* Change the current working directory to test directory
  * `cd test`
* Run the test scripts
  * `make test`
