date
start_ts=`date +"%s"`

max_idx=1000
. /Users/terzeron/.bashrc
script_path=$(dirname $0)
#echo script_path=${script_path}
. ${script_path}/setup.sh
#echo FEED_MAKER_HOME=${FEED_MAKER_HOME}

runlog=run.log
errorlog=error.log

function send_error_msg
{
    #id="terzeron"
    #curl -Sso/dev/null "http://ssea.naver.com:20000/smsg?id=$id&method=email&subject=feedmaker&msg=$1"
	#echo "curl -Sso/dev/null http://ssea.naver.com:20000/smsg?id=$id&method=email&subject=feedmaker&msg=$1"
	#echo "$1" | mail -s "feedmaker error" terzeron@gmail.com
    #echo "send error message '$1'"
	#echo "email function is not supported"
	echo "$1" | mail -s "FeedMaker error" 5jkfokr6ggh8@bxc.io
}

function execute_job
{
	dir=$1
	#echo $dir
	if [ -d "$dir" -a -f "$dir/conf.xml" ]; then
		#echo -n $dir "  "
		is_completed=$(grep "<is_completed>true" $dir/conf.xml)
		recent_collection_list=$(find $dir/newlist -type f -mmin 144)
		rm -f $runlog $errorlog
		if [ "$is_completed" != "" -a "$recent_collection_list" == "" ]; then
			(cd $dir; run.sh -c > $runlog 2> $errorlog; run.sh >> $runlog 2>> $errorlog)
		else
			(cd $dir; run.sh > $runlog 2> $errorlog)
		fi
	fi
}

echo "deleting old or zero-size image files..."
find /Users/terzeron/public_html/xml/img \( -mtime +20d -o -size 0 \) -exec rm -rf "{}" \; -ls

cd ${FEED_MAKER_HOME}
pwd

dirs=( $(find . -type d \! \( -name "_*" -o -name .git -o -name . -o -name newlist -o -name html \) | perl -MList::Util=shuffle -e 'print shuffle <STDIN>') )
for i in $(seq 0 5 $max_idx); do
#for i in $(seq 0 1 $max_idx); do
	if [ "${dirs[$i]}" == "" ]; then
		break
	fi
	execute_job ${dirs[$((i+0))]} &
	execute_job ${dirs[$((i+1))]} &
	execute_job ${dirs[$((i+2))]} &
	execute_job ${dirs[$((i+3))]} &
	execute_job ${dirs[$((i+4))]} &
	wait
	#execute_job ${dirs[$i]}	
done
echo 

for d in $dirs; do 
	if [ -d "$d" -a -f "$d/conf.xml" ]; then
		if [ -s $d/$errorlog ]; then
			echo "===================="
			echo $d
			echo "===================="
			egrep -i -e "(error)" $d/$errorlog && list="$list,${d##*/}"
		fi
	fi
done

echo "list='$list'"
if [ "$list" != "" ]; then
	echo "sending error messge"
	send_error_msg "$list"
fi

find_problems.sh > log/find_problems.log 2>&1

date
end_ts=`date +"%s"`
echo "elapse="$(($end_ts-$start_ts))
