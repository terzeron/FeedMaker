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
