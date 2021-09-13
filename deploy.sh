#!/bin/bash

(cd frontend; npm run build) && scp -r -P 20023 frontend/dist terzeron.com:~/public_html/fmw/frontend/
scp -r -P 20023 backend/*.py backend/index.wsgi backend/requirements.txt terzeron.com:~/public_html/fmw/backend/

echo "git switch develop"
git switch develop > /dev/null
echo "git push"
git push > /dev/null
echo "git switch master"
git switch master > /dev/null
echo "git merge develop"
git merge develop > /dev/null
echo "git push"
git push > /dev/null
echo "git switch develop"
git switch develop > /dev/null
