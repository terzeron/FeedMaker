#!/bin/bash

if [ -z "${FEED_MAKER_HOME_DIR}" ]; then
	echo "FEED_MAKER_HOME_DIR environment variable is not declared"
	exit -1
fi

cd $FEED_MAKER_HOME_DIR
find . \( \
	-name "*.html" -o \
	-name "*.txt" -o \
	-name "*.log" -o \
	\( -name "*.xml" -a \! -name conf.xml -a \! -name test.config.xml \) -o \
	\( -name "*.xml.old" -a \! -name conf.xml.old \) \
	\) -exec rm -f "{}" \;
find . \( -name newlist -o -name html \) -exec rm -rf "{}" \;
