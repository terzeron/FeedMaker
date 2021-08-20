# Installation
* frontend
  * `cd frontend`
  * `npm install`
* backend
  * `cd backend`
  * `pip install -r requirements.txt`
  
# Run
* API
  * in production mode
    * `flask run`
  * in development mode
    * `env FLASK_ENV=development FLASK_APP=index.py flask run`
  * access test
    * `curl localhost:5000/fm/groups`
    * `curl localhost:5000/fm/groups/agit/feeds`
    * `curl localhost:5000/fm/groups/agit/feeds/gang_with_sword`
