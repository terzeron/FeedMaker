# FeedMaker

Utility set and web admin page for making feeds from crawling websites

# Components
* bin & utils
  * CLI utilities and feed maker engine
* backend
  * API
* frontend
  * Vue application

# for users

## Requirements

* Python3 & modules
  * bs4, PyRSS2Gen, selenium, ...
  * `pip install -r requirements.txt`
* chromedriver
  * http://chromedriver.chromium.org/downloads
  * You should download chromedriver appropriate for chrome browser installed on your system. And this binary must be located in PATH environment variable.
  * Also you should install chrome browser.
* pdf libraries (optional)
  * pdf2image
    * `sudo apt install poppler-utils`
    * If you have some trouble in installting poppler-utils, then
        * `sudo apt install build-essential libpoppler-cpp-dev pkg-config`
* FeedMaker & FeedMakerApplications
  * https://github.com/terzeron/FeedMaker/archive/master.zip
  * https://github.com/terzeron/FeedMakerApplications/archive/master.zip
  * You would be good to use $HOME/workspace/fm & $HOME/workspace/fma for these projects.
    * ex) export FEED_MAKER_HOME_DIR=$HOME/workspace/fm
    * ex) export FEED_MAKER_WORK_DIR=$HOME/workspace/fma
  
## Usage

* Apply environment variables
  * `. <feedmaker installation dir>/bin/setup.sh`
  * ex) `. $HOME/workspace/fm/bin/setup.sh`
* Change the current working directory to a feed directory
  * `cd $FEED_MAKER_WORK_DIR/<groupdir>/<feeddir>`
  * ex) `cd $FEED_MAKER_WORK_DIR/naver/navercast.118`
* Run the FeedMaker for a current feed
  * `run.py`
* Run the FeedMaker for all feeds
  * `cd $FEED_MAKER_WORK_DIR`
  * `run.py -a`
  
## Test

* Apply environment variables 
  * `. <feedmaker installation dir>/bin/setup.sh`
* Change the current working directory to test directory
  * `cd test`
* Run the test scripts
  * `make test`

# for developers and web admins

## Installation
* frontend
  * `cd frontend`
  * `npm install`
* backend
  * `cd backend`
  * `pip install -r requirements.txt`

## Build & Deploy
* backend
  * Copy the backend directory to your ~/public_html or /var/www/html
  * Otherwise, configure web server settings to be connected to the backend directory 
  * modify index.wsgi to configure your environment.
  * touch index.wsgi whenever you modify flask app codes.
* frontend
  * `cd frontend`
  * `npm run build`
  * You can use static files in dist/ directory.
  * Copy dist/ directory to your installation directory where the backend is deployed.
* example of installation directory
  * ~/public_html/fmw
    * backend
      * dist

## Run
* API
  * in production mode
    * You can use Nginx & uwsgi or Apache HTTPd & mod_wsgi. No need to consider flask runtime.
      * Refer to the following setting guide. 
      * access test
        * API: `curl your.api.domain.com/fm/groups`
        * Web: `curl your.web.domain.com`
  * in development mode
    * You must run flask and vue dev server for yourself.
      * Flask: `env FLASK_ENV=development flask run`
      * Vue: `npm run serve`
      * access test
        * API: `curl localhost:5000/groups`
        * Web: `curl localhost:8080`
      
## Nginx & Flask interconnection settings

### Web(frontend) Nginx settings
* Add a new file `<nginx configuration dir>/servers/fm.conf`
* You must modify `FEEDMAKER_BACKEND_DIR` and `FEEDMAKER_FRONTEND_DIR` to real paths and some uppercase variables to real values.

#### fm.conf
```
server {
    listen 80_FOR_PRODUCTION_OR_8082_FOR_DEVELOPMENT;
    server_name YOUR_DOMAIN_NAME_OR_127_DOT_0_DOT_0_DOT_1;

    location / {
        include      uwsgi_params;
        uwsgi_pass   unix:FEEDMAKER_BACKEND_DIR/uwsgi.sock;
    }
    location /css {
        root FEEDMAKER_FRONTEND_DIR/dist;
    }
    location /js {
        root FEEDMAKER_FRONTEND_DIR/dist;
    }
}
```

`nginx`
or 
`nginx -g "daemon off;"`

#### uwsqi.ini
```
[uwsgi]
module = app:app

processes = 5
socket = ./uwsgi.sock
chmod-socket = 666
pidfile = ./uwsgi.pid
demonize = ./logs/uwsgi.log

plugins-dir = /usr/local/Cellar/uwsgi/2.0.19.1_2/libexec/uwsgi
plugin = python3

log-reopen = true
die-on-term = true
master = true
vacuum = true
```

`uwsgi --ini uwsgi.ini`

* You can this web service by http://localhost:8082
* Also, try http://localhost:8082/groups

## Apache HTTPd & Flask interconnection settings
* You must modify `FEEDMAKER_BACKEND_DIR` and `FEEDMAKER_FRONTEND_DIR` to real paths.

### Web(frontend) Apache HTTPd settings
* to serve index.html
  * DocumentRoot FEEDMAKER_FRONTEND_DIR/dist
  * ex) DocumentRoot /home/user/public_html/fmw/frontend/dist
```
DocumentRoot FEEDMAKER_FRONTEND_DIR/dist
<Directory FEEDMAKER_FRONTEND_DIR/dist>
    RewriteEngine On
    AllowOverride All
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    RewriteRule . /index.html [L]
</Directory>
```

If you have .htaccess RewriteEngine issue like 403 Forbidden error, add this configuration.
```
<Directory WWW_ROOT_DIR>
    RewriteEngine On
    AllowOverride All
</Directory>
``` 

## API(backend) Apache HTTPd settings
```
<Directory FEEDMAKER_BACKEND_DIR>
    RewriteEngine On
    AllowOverride All
</Directory>

<IfModule wsgi_module>
    WSGIDaemonProcess fmw user=user group=user threads=2
    WSGIScriptAlias /fm FEEDMAKER_BACKEND_DIR/index.wsgi
    <Directory FEEDMAKER_BACKEND_DIR>
        WSGIProcessGroup fmw
        WSGIApplicationGroup %{GLOBAL}
        Require all granted
    </Directory>
</IfModule>
```

## API(backend) Flask settings
* index.wsgi
  * `sys.path.insert(0, 'FEEDMAKER_BACKEND_DIR')`
* app.py
  * `@app.route("/groups", methods=["GET"])`
  * Apache mounts this Flask app on /fm path. So all routes in app.py should be relative path such as '/groups'.
* URLs and paths in all codes
  * frontend: `axios.get('https://your.domain.com/fm/groups')`
  * apache: `WSGIScriptAlias /fm FEEDMAKER_BACKEND_DIR/index.wsgi`
  * index.wsgi: `sys.path.insert(0, 'FEEDMAKER_BACKEND_DIR')`
  * app.py: `@app.route("/groups", methods=["GET"])`
