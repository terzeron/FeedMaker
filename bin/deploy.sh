#!/bin/bash

FEED_MAKER_HOME=/Users/terzeron/workspace/fm
FEED_MAKER_HOME_DEV=/Users/terzeron/workspace/fmd

cd $FEED_MAKER_HOME_DEV
git checkout master
git pull
git merge develop --no-edit
git pull
git push
git checkout develop

cd $FEED_MAKER_HOME
git checkout master
git pull
