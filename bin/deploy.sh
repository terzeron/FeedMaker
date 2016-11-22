#!/bin/bash

FEED_MAKER_HOME=/Users/terzeron/workspace/fm
FEED_MAKER_HOME_DEV=/Users/terzeron/workspace/fmd

cd $FEED_MAKER_HOME_DEV
pwd
echo 

echo "git checkout master"
git checkout master
echo

echo "git pull"
git pull
echo

echo "git merge develop"
git merge develop
echo

echo "git push"
git push
echo 

echo "git checkout develop"
git checkout develop

cd $FEED_MAKER_HOME
pwd
echo

echo "git checkout master"
git checkout master
echo

echo "git pull"
git pull
echo