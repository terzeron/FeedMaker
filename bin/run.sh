date

# 옵션처리
REMOVE_HTMLS=0
FORCE_COLLECT_OPT=""
while getopts "hrc" arg; do
	case $arg in
		h) 
			echo "usage: $0 [-h] [-r] [-c]"; 
			echo "  -h: print usage"
			echo "  -r: remove html files"
			echo "  -c: force collect"
			;;
		r) 
			REMOVE_HTMLS=1
			;;
		c)
			FORCE_COLLECT_OPT="-c"
			;;
	esac
done

# 첫번째 파라미터를 피드 디렉토리로 간주하고 chdir
if [ -d "$1" ]; then
	cd $1
fi

# html 디렉토리에서 60일 이상 오래된 파일을 삭제함
if [ -d html ]; then
	grep -q "<is_completed>true</is_completed>" conf.xml || (echo "deleting old html files"; find html -mtime +60d -exec rm -f "{}" \; -ls)
fi

# -r 옵션이 켜져 있으면 일부 파일을 미리 삭제함
if [ ${REMOVE_HTMLS} -eq 1 ]; then
	img_list=`perl -ne 'if (m!xml/img/(\w+\.jpg)!) { print $1 . "\n"; }' html/* *.xml *.xml.old`
	for f in $img_list; do 
		rm -f ~/public_html/xml/img/$f;
	done
	rm -rf newlist html start_idx.txt
fi

# 다운로드 안 된 이미지를 포함한 html을 지움
# html은 60일 이내의 최신 파일만 해당함 (60일 이상 오래된 파일은 무시)
for f in `find html -name "*.html" -mtime -60d -exec grep -q "<img src=.http://terzeron\.net/xml/img/" "{}" \; -print`; do
	b=0
	for i in `perl -ne 'if (m!<img src=.http://terzeron\.net/xml/img/([^.]+\.jpg)!) { print $1 . "\n"; }' $f`; do
		if [ ! -e /Users/terzeron/public_html/xml/img/"$i" ]; then
			b=1
			last_img=$i
			break
		fi      
	done
	if [ "$b" == 1 ]; then
		# 완결된 피드는 이미지를 다시 다운로드하라고 메시지를 출력하고
		# 해당 html을 삭제
		grep -q "<is_completed>true</is_completed>" conf.xml && echo "need to re-download images like '$last_img' in '$f'"; (echo "deleting '$f' for missing image '$last_img'"; ls -alF "$f"; rm -f "$f")
	fi
done

start_ts=`date +"%s"`
PKGID=`basename $PWD`
RESULT_XML=$PKGID.xml
make_feed.pl $FORCE_COLLECT_OPT $RESULT_XML

rm -f cookie.txt nohup.out

date
end_ts=`date +"%s"`
echo "elapse="$(($end_ts-$start_ts))
