#!/bin/bash

. ~/workspace/fm/bin/setup.sh

export FEED_MAKER_HOME_DIR=$HOME/workspace/fm
export FEED_MAKER_WORK_DIR=$(dirname $FEED_MAKER_HOME_DIR)/fma
export FEED_MAKER_LOG_DIR=$FEED_MAKER_WORK_DIR/logs
export FEED_MAKER_WWW_ADMIN_DIR=$HOME/public_html/fm
export FEED_MAKER_WWW_FEEDS_DIR=$HOME/public_html/xml
export CARTOON_SPLIT_HOME_DIR=$HOME/workspace1/cs.dev
export PATH=$FEED_MAKER_HOME_DIR/bin:$CARTOON_SPLIT_HOME_DIR:$PATH
export PYTHONPATH=$FEED_MAKER_HOME_DIR/bin:$PYTHONPATH
export LOG_DIR=$HOME/logs

site_list=$*
for site in $site_list; do
    echo $site
    log=$LOG_DIR/check_manga_${site}.log
    searchresult=$LOG_DIR/search_manga_${site}.result.log
    searcherror=$LOG_DIR/search_manga_${site}.error.log
    
    cd $FEED_MAKER_WORK_DIR/$site
    check_manga_site.py > $log 2>&1 || \
        (echo "error in checking $site"; date; cat $log | send_msg_to_gmail.sh -s "error in checking $site")

    if [ "${site%"${site#?}"}" != "_" ]; then
        keyword=$(cat site_config.json | jq -r .keyword)
        search_manga_site.py -s $site "$keyword" > $searchresult 2> $searcherror
        num_lines=$(cat $searchresult | wc -l)
        if [ "$num_lines" -ne 0 -a "$num_lines" -lt 3 ]; then
            echo "error in searching '$keyword' in $site"; date;
            (echo "error in searching '$keyword' in $site"; cat $searcherror) | send_msg_to_gmail.sh -s "error in search $site"
        fi
    fi
    sleep 5
done

