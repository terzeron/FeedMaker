#!/bin/bash

FEED_MAKER_HOME_DIR=$HOME/workspace/fm
FEED_MAKER_HOME_DEV_DIR=$HOME/workspace/fm.dev

(cd $FEED_MAKER_HOME_DEV_DIR/bin; etags *.py)

echo "--------------------"
cd $FEED_MAKER_HOME_DEV_DIR
pwd
echo

echo "--------------------"
echo "git switch master"
git switch master
echo

echo "--------------------"
echo "git pull"
git pull
echo

echo "--------------------"
echo "git merge develop"
git merge develop --no-edit
echo

echo "--------------------"
echo "git push"
git push
echo

echo "--------------------"
echo "git switch develop"
git switch develop

echo "--------------------"
cd $FEED_MAKER_HOME_DIR
pwd
echo

echo "--------------------"
echo "git switch master"
git switch master
echo

echo "--------------------"
echo "git pull"
git pull
echo

echo "--------------------"
echo "pip3 install"
pip3 install -r requirements.txt | grep -v "Requirement already satisfied"
echo
