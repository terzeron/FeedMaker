# determine the feedmaker home from current working directory
# ex) /home1/terzeron/work/fm.dev/naver --> /home1/terzeron/work/fm.dev
# ex) /Users/terzeron/FeedMaker/cnn/news -> /Users/terzeron/FeedMaker
if [ "$0" != "-bash" ]; then
	# ex) called from all.sh
	path=$(dirname $0)
else
	# ex) . ../../bin/setup.sh
	path=${PWD}/
fi
export FEED_MAKER_HOME=$(echo $path | gsed -r 's/((fm|[Ff]eed[Mm]aker)[^\/]*).*/\1/')
echo FEED_MAKER_HOME=${FEED_MAKER_HOME}

BIN_DIR=${FEED_MAKER_HOME}/bin
export PATH=~/bin:.:${BIN_DIR}:/usr/local/bin/:/usr/local/sbin:/bin:/sbin:/usr/bin:/usr/sbin:${PATH}

# python path
export PYTHONPATH=${BIN_DIR}:/usr/local/lib/python2.7/site-packages:${PYTHONPATH}

# perl path
export PERLBREW_ROOT=/Users/terzeron/perl5/perlbrew
. ${PERLBREW_ROOT}/etc/bashrc
PERL_INSTALLED_VERSION=5.19.11
export PERL5LIB=${PERLBREW_ROOT}/perls/perl-${PERL_INSTALLED_VERSION}/lib/site_perl/${PERL_INSTALLED_VERSION}:.:${BIN_DIR}

. "`brew --prefix grc`/etc/grc.bashrc"

