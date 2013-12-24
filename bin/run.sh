date
REMOVE_HTMLS=0
if [ "$1" == "-f" ]; then
	REMOVE_HTMLS=1
fi
shift

if [ -d "$1" ]; then
	cd $1
fi

if [ -d html ]; then
	grep -q "<is_completed>true</is_completed>" conf.xml || (echo "deleting old html files"; find html -mtime +120d -exec rm -f "{}" \; -ls)
fi

# -f 옵션이 켜져 있으면 일부 파일을 미리 삭제함
if [ ${REMOVE_HTMLS} -eq 1 ]; then
	img_list=`perl -ne 'if (m!xml/img/(\w+\.jpg)!) { print $1 . "\n"; }' html/* *.xml *.xml.old`
	for f in $img_list; do 
		rm -f ~/public_html/xml/img/$f;
	done
	rm -rf newlist html start_idx.txt
fi

# 다운로드 안 된 이미지를 포함한 html을 지움
# html은 14일 이내의 최신 파일만 해당함 (14일 이상 오래된 파일은 무시)
for f in `find html -name "*.html" -mtime -14d -exec grep -q "<img src=.http://terzeron\.net/xml/img/" "{}" \; -print`; do
	b=0
	for i in `perl -ne 'if (m!<img src=.http://terzeron\.net/xml/img/([^.]+\.jpg)!) { print $1 . "\n"; }' $f`; do
		if [ ! -e /Users/terzeron/public_html/xml/img/"$i" ]; then
			b=1
			last_img=$i
			break
		fi      
	done
	if [ "$b" == 1 ]; then
		grep -q "<is_completed>true</is_completed>" conf.xml && echo "need to re-download images like '$last_img' in '$f'" || (echo "deleting '$f' for missing image '$last_img'"; ls -alF "$f"; rm -f "$f")
	fi
done

start_ts=`date +"%s"`
PKGID=`basename $PWD`
RESULT_XML=$PKGID.xml
make_feed.pl $RESULT_XML

rm -f cookie.txt nohup.out
date
end_ts=`date +"%s"`
echo "elapse="$(($end_ts-$start_ts))
