# You should change this environment variables according to your environment.

# engine directory
export FEED_MAKER_HOME_DIR=$HOME/workspace/fm.dev
# feed working directory
export FEED_MAKER_WORK_DIR=$HOME/workspace/fma
export FEED_MAKER_LOG_DIR=$FEED_MAKER_WORK_DIR/logs
# admin console web page directory
export FEED_MAKER_WWW_ADMIN_DIR=$HOME/public_html/fm
# feed directory public to feed crawlers
export FEED_MAKER_WWW_FEEDS_DIR=$HOME/public_html/xml
# CartoonSplit utilities
export CARTOON_SPLIT_HOME_DIR=$HOME/workspace/cs.dev

export PATH=$FEED_MAKER_HOME_DIR/bin:$CARTOON_SPLIT_HOME_DIR:$PATH
export PYTHONPATH=$FEED_MAKER_HOME_DIR/bin:$PYTHONPATH

