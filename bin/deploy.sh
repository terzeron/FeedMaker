#!/bin/bash

FEED_MAKER_HOME=/Users/terzeron/workspace/fm
FEED_MAKER_HOME_DEV=/Users/terzeron/workspace/fmd

cd $FEED_MAKER_HOME_DEV
pwd
<<<<<<< HEAD
echo 
=======
echo
>>>>>>> develop

echo "--------------------"
echo "git checkout master"
git checkout master
echo

echo "--------------------"
echo "git pull"
git pull
git merge develop --no-edit
git pull
git push
<<<<<<< HEAD
echo 
=======
echo
>>>>>>> develop

echo "--------------------"
echo "git checkout develop"
git checkout develop

cd $FEED_MAKER_HOME
pwd
echo

echo "--------------------"
echo "git checkout master"
git checkout master
echo

echo "--------------------"
echo "git pull"
git pull
echo
