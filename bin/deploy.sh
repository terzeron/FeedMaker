#!/bin/bash

FEED_MAKER_HOME=$HOME/workspace/fm
FEED_MAKER_HOME_DEV=$HOME/workspace/fm.dev

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
