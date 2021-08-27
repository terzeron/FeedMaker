# You should change this environment variables according to your environment.

export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
if command -v pyenv 1>/dev/null 2>&1; then
  eval "$(pyenv init --path)"
  eval "$(pyenv init -)" > /dev/null 2>&1
  eval "$(pyenv virtualenv-init -)"
fi

# engine directory
export FEED_MAKER_HOME_DIR=$(dirname $(dirname $(readlink -f $0)))
# feed working directory
export FEED_MAKER_WORK_DIR=$(dirname $FEED_MAKER_HOME_DIR)/fma
export FEED_MAKER_LOG_DIR=$FEED_MAKER_WORK_DIR/logs
# admin console web page directory
export FEED_MAKER_WWW_ADMIN_DIR=$HOME/public_html/fm
# feed directory public to feed crawlers
export FEED_MAKER_WWW_FEEDS_DIR=$HOME/public_html/xml
# CartoonSplit utilities
export CARTOON_SPLIT_HOME_DIR=$HOME/workspace/cs.dev

export PATH=$FEED_MAKER_HOME_DIR/bin:$CARTOON_SPLIT_HOME_DIR:$PATH
export PYTHONPATH=$FEED_MAKER_HOME_DIR/bin:$PYTHONPATH
