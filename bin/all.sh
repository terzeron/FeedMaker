date
start_ts=`date +"%s"`

max_idx=1000
runlog=run.log
errorlog=error.log
collectorerrorlog=collector.error.log

function send_error_msg() {
    curl -X POST \
         -H 'Content-Type:application/json' \
         -H 'Authorization: Bearer gdrao6YPr50SCzwqb7By40yqwOotDdo9a/+nGYmFkL3xMUA1P3OPJO7aKlNTnN12tz0BzJ5C/TX+gTZiIUFeXIa8X1reFHNXPcJ/hlZysxTkBOkSzbEI/TUbBVDjves+lDqDwVicBisE3/MelN5QrAdB04t89/1O/w1cDnyilFU=' \
         -d '{
             "to": "U52aa71b262aa645ba5f3e4786949ef23",
             "messages":[    
             {
                "type":"text",
                "text":"'"$1"'"
             }
             ]
             }' https://api.line.me/v2/bot/message/push
}

function execute_job() {
	dir=$1
	#echo $dir
	if [ -d "$dir" -a -f "$dir/conf.xml" ]; then
		echo $dir "  "
		is_completed=$(grep "<is_completed>true" $dir/conf.xml)
		recent_collection_list=$([ -e "$dir/newlist" ] && find $dir/newlist -type f -mtime +72)
		rm -f $runlog $errorlog $collectorerrorlog
		if [ "$is_completed" != "" -a "$recent_collection_list" == "" ]; then
			(cd $dir; run.sh -c > $runlog 2> $errorlog; run.sh >> $runlog 2>> $errorlog)
		else
			(cd $dir; run.sh > $runlog 2> $errorlog)
		fi
	fi
}

echo "deleting old or zero-size image files..."
count=$(find $FEED_MAKER_WWW_FEEDS/img \( -mtime +60d -o -size 0 \) -delete | wc -l)
echo "$count files deleted"

dirs=( $(find . -type d -path "./*/*" -not \( -path "./.git/*" -o -path "./_*/*" -o -path "./*/_*" -o -name newlist -o -name html \) | perl -MList::Util=shuffle -e 'print shuffle <STDIN>') )
#for i in $(seq 0 5 $max_idx); do
for i in $(seq 0 1 $max_idx); do
	if [ "${dirs[$i]}" == "" ]; then
		break
	fi
	#execute_job ${dirs[$((i+0))]} &
	#execute_job ${dirs[$((i+1))]} &
	#execute_job ${dirs[$((i+2))]} &
	#execute_job ${dirs[$((i+3))]} &
	#execute_job ${dirs[$((i+4))]} &
	#wait
	execute_job ${dirs[$i]}	
done
echo 

for i in $(seq 0 1 $max_idx); do
    if [ "${dirs[$i]}" == "" ]; then
        break
    fi
    d=${dirs[$i]}
	if [ -d "$d" -a -f "$d/conf.xml" ]; then
		if [ -s $d/$errorlog ]; then
			echo "===================="
			echo $d
			echo "===================="
			egrep -i -v -e "Warning" $d/$errorlog && list="$list,${d##*/}"
		fi
	fi
done

echo "list='$list'"
if [ "$list" != "" ]; then
	echo "sending error messge"
	send_error_msg "$list"
fi

find_problems.sh > logs/find_problems.log 2>&1

date
end_ts=`date +"%s"`
echo "elapse="$(($end_ts-$start_ts))
