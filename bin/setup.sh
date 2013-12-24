export FEED_MAKER_HOME=/Users/terzeron/workspace/feedmaker
BIN_DIR=${FEED_MAKER_HOME}/bin
export PATH=~/bin:.:${BIN_DIR}:/usr/local/bin/:/usr/local/sbin:/bin:/sbin:/usr/bin:/usr/sbin:${PATH}
export PYTHONPATH=${BIN_DIR}:/usr/local/lib/python2.7/site-packages:${PYTHONPATH}

export PERLBREW_ROOT=/Users/terzeron/perl5/perlbrew
. ${PERLBREW_ROOT}/etc/bashrc
PERL_INSTALLED_VERSION=5.19.5
export PERL5LIB=${PERLBREW_ROOT}/perls/perl-${PERL_INSTALLED_VERSION}/lib/site_perl/${PERL_INSTALLED_VERSION}:.:${BIN_DIR}

. "`brew --prefix grc`/etc/grc.bashrc"

