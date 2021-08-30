#!/bin/bash

git switch develop
git push
git switch master
git merge develop
git switch develop
(cd frontend; npm run build) && scp -r -P 20023 frontend/dist terzeron.com:~/public_html/fmw/frontend/
scp -r -P 20023 backend/*.py backend/index.wsgi backend/requirements.txt terzeron.com:~/public_html/fmw/backend/
