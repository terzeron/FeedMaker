#!/bin/bash

FEED_MAKER_HOME=/Users/terzeron/workspace/fm
FEED_MAKER_HOME_DEV=/Users/terzeron/workspace/fm.dev

echo "--------------------"
cd $FEED_MAKER_HOME_DEV
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

echo "--------------------"
echo "git merge develop"
git merge develop --no-edit
echo

echo "--------------------"
echo "git push"
git push
echo

echo "--------------------"
echo "git checkout develop"
git checkout develop

echo "--------------------"
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
