# Installation
* frontend
  * `cd frontend`
  * `npm install`
* backend
  * `cd backend`
  * `pip install -r requirements.txt`

# Build & Deploy
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

# Run
* API
  * in production mode
    * You can use apache and wsgi.
  * in development mode
    * `env FLASK_ENV=development flask run`
  * access test
    * `curl localhost:5000/fm/groups`
    * `curl localhost:5000/fm/groups/agit/feeds`
    * `curl localhost:5000/fm/groups/agit/feeds/gang_with_sword`

# Apache & Flask interaction settings
## Web(frontend) Apache settings
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
  * `sys.path.insert(0, '/home/terzeron/public_html/fmw/backend')`
* app.py
  * `@app.route("/groups", methods=["GET"])`
  * Apache mounts this Flask app on /fm path. So all routes in app.py should be relative path such as '/groups'.
* URLs and paths in all codes
  * frontend: `axios.get('https://userdomain.com/fm/groups')`
  * apache: `WSGIScriptAlias /fm /home/user/public_html/fmw/backend/index.wsgi`
  * index.wsgi: `sys.path.insert(0, '/home/terzeron/public_html/fmw/backend')`
  * app.py: `@app.route("/groups", methods=["GET"])`
