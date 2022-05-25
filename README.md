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
  
## Usage

* Apply environment variables
  * `. <feedmaker dir>/bin/setup.sh`
  * ex) `. $HOME/workspace/fm/bin/setup.sh`
* Change the current working directory to a feed directory
  * `cd <application dir>/<sitedir>/<feeddir>`
  * ex) `cd $HOME/workspace/fma/naver/navercast.118`
* Run the FeedMaker
  * `run.py`

## Test

* Apply environment variables 
  * `. <feedmaker dir>/bin/setup.sh`
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

## Modify configuration
* frontend
  * `mv .env.development.example .env.development`
  * `mv .env.production.example .env.production`
  * `vi .env.development.example .env.production.example`
    * You should write your own Facebook APP ID and admin email address.

## Build & Deploy
* backend
  * Copy backend directory to your ~/public_html or /var/www/html.
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
    * You can use apache and wsgi.
  * in development mode
    * `env FLASK_ENV=development flask run`
  * access test
    * `curl localhost:5000/fm/groups`
    * `curl localhost:5000/fm/groups/agit/feeds`
    * `curl localhost:5000/fm/groups/agit/feeds/gang_with_sword`

## Apache & Flask interaction settings

### Web(frontend) Apache settings
* to serve index.html
  * DocumentRoot /<installation_path_of_project>/frontend/dist
  * ex) DocumentRoot /home/user/public_html/fmw/frontend/dist
```
DocumentRoot /home/user/public_html/fmw/frontend/dist
<Directory /home/user/public_html/fmw/frontend/dist>
    RewriteEngine On
    AllowOverride All
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    RewriteRule . /index.html [L]
</Directory>
```

If you have .htaccess RewriteEngine issue, add this configuration
```
<Directory /home/user/public_html>
    RewriteEngine On
    AllowOverride All
</Directory>
``` 

## API(backend) Apache settings
```
<Directory /home/user/public_html/fmw/backend>
    RewriteEngine On
    AllowOverride All
</Directory>

<IfModule wsgi_module>
    WSGIDaemonProcess fmw user=user group=user threads=2
    WSGIScriptAlias /fm /home/user/public_html/fmw/backend/index.wsgi
    <Directory /home/user/public_html/fmw/backend>
        WSGIProcessGroup fmw
        WSGIApplicationGroup %{GLOBAL}
        Require all granted
    </Directory>
</IfModule>
```

## API(backend) Flask settings
* index.wsgi
  * /home/user/public_html/fmw/backend/index.wsgi
  * `sys.path.insert(0, '/home/user/public_html/fmw/backend')`
* app.py
  * `@app.route("/groups", methods=["GET"])`
  * Apache mounts this Flask app on /fm path. So all routes in app.py should be relative path such as '/groups'.
* URLs and paths in all codes
  * frontend: `axios.get('https://userdomain.com/fm/groups')`
  * apache: `WSGIScriptAlias /fm /home/user/public_html/fmw/backend/index.wsgi`
  * index.wsgi: `sys.path.insert(0, '/home/user/public_html/fmw/backend')`
  * app.py: `@app.route("/groups", methods=["GET"])`
