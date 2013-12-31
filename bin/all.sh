date
start_ts=`date +"%s"`

MAX_IDX=1000
FEED_MAKER_HOME=/Users/terzeron/workspace/FeedMaker
BIN_DIR=${FEED_MAKER_HOME}/bin
. /Users/terzeron/.bashrc
. ${BIN_DIR}/setup.sh

runlog=run.log
errorlog=error.log

function send_error_msg
{
    #id="terzeron"
    #curl -Sso/dev/null "http://ssea.naver.com:20000/smsg?id=$id&method=email&subject=feedmaker&msg=$1"
	#echo "curl -Sso/dev/null http://ssea.naver.com:20000/smsg?id=$id&method=email&subject=feedmaker&msg=$1"
	echo "$1" | mail -s "feedmaker error" terzeron@gmail.com
    echo "send error message '$1'"
}

function execute_job
{
	dir=$1
	#echo $dir
	if [ -d "$dir" -a -f "$dir/conf.xml" ]; then
		#echo -n $dir "  "
		(cd $dir; run.sh > $runlog 2> $errorlog)
	fi
}

echo "deleting old image files..."
find /Users/terzeron/public_html/xml/img \( -mtime +30d -o -size 0 \) -exec rm -f "{}" \; -ls

cd ${FEED_MAKER_HOME}
pwd

dirs=(`find . -type d \! \( -name "_*" -o -name .git -o -name . -o -name newlist -o -name html \)`)
for i in $(seq 0 5 $MAX_IDX); do
#for i in $(seq 0 1 $MAX_IDX); do
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

for f in */*; do 
	if [ -d "$f" -a -f "$f/conf.xml" ]; then
		if [ -s $f/$errorlog ]; then
			echo "===================="
			echo $f
			echo "===================="
			cat $f/$errorlog
			egrep -i -e "(error)" $f/$errorlog && list="$list,${f##*/}"
		fi
	fi
done

echo "list='$list'"
if [ "$list" != "" ]; then
	echo "sending error messge"
	#send_error_msg "$list"
fi

find_problems.sh > log/find_problems.log 2>&1

date
end_ts=`date +"%s"`
echo "elapse="$(($end_ts-$start_ts))
