# FeedMaker

Utility set and web admin page for making feeds from crawling websites

# Components
* bin & utils
  * CLI utilities and feed maker engine
* backend
  * API
* frontend
  * Vue application
  
## Test

* Apply environment variables 
  * `. <feedmaker installation dir>/bin/setup.sh`
* Change the current working directory to test directory
  * `cd test`
* Run the test scripts
  * `make test`

### Deploy

* ./build.sh
* ./run_in_local.sh
* ./deploy_to_k8s.sh

