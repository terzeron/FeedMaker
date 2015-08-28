#!/bin/bash

FEED_MAKER_HOME=/Users/terzeron/fm
FEED_MAKER_HOME_DEV=/Users/terzeron/fmd

cd $FEED_MAKER_HOME_DEV
git checkout master
git pull
git merge develop
git pull
git push
git checkout develop

cd $FEED_MAKER_HOME
git checkout master
git pull
