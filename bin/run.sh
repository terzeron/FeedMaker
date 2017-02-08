date
start_ts=`date +"%s"`

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
            exit 1
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

PKGID=`basename $PWD`
RESULT_XML=$PKGID.xml
IMG_DIR=$FEED_MAKER_WWW_FEEDS"/img/${PKGID}"
is_completed=$(grep -q "<is_completed>true</is_completed>" conf.xml && echo 1 || echo 0)

# html 디렉토리에서 20일 이상 오래된 파일을 삭제함
if [ -d html ]; then
    [ "$is_completed" == "1" ] || (echo "deleting old html files"; find html/ -type f -mtime +20d -delete -ls)
fi

# -r 옵션이 켜져 있으면 일부 파일을 미리 삭제함
if [ ${REMOVE_HTMLS} -eq 1 ]; then
    [ -d "${IMG_DIR}" ] && find ${IMG_DIR} -type f -delete
    rm -rf newlist html start_idx.txt
fi

# 다운로드 안 된 이미지를 포함한 html을 지움
for f in `[ -d html ] && find html -name "*.html" -exec egrep -q "<img.*https?://terzeron\.net/xml/img/" "{}" \; -print`; do
    b=0
    for i in `perl -ne 'if (m!<img src=.http://terzeron\.net/xml/img/[^/]+/(.+\.jpg)!) { print $1 . "\n"; }' $f`; do
        if [ ! -e ${IMG_DIR}/"$i" ]; then
            b=1
            last_img=$i
            break
        fi      
    done
    if [ "$b" == 1 ]; then
        # 완결된 피드는 이미지를 다시 다운로드하라고 메시지를 출력하고
        # 해당 html을 삭제
        [ "$is_completed" == "1" ] && echo "need to re-download images like '$last_img' in '$f'"; (echo "deleting '$f' for missing image '$last_img'"; ls -alF "$f"; rm -f "$f")
    fi
done

make_feed.py $FORCE_COLLECT_OPT $RESULT_XML

# 불필요한 파일 삭제
rm -f cookie.txt nohup.out
# 불필요한 이미지 삭제
if [ "$is_completed" != "1" ]; then
    perl -e '
    my %img_map = ();
    while (my $line = <ARGV>) {
        if ($line =~ m!img src=.http://terzeron\.net/xml/img/[^/]+/(.+\.jpg)!) {
            $img_map{$1} = 1;
        }
    }
    opendir(my $dh, "'${IMG_DIR}'");
    while(my $f = readdir $dh) {
        if ($f eq "." or $f eq "..") {
            next;
        }
        if (not exists $img_map{$f} and $img_map{$f} != 1 and -f "'${IMG_DIR}'/$f") {
            print "removing '${IMG_DIR}'/$f\n";
            unlink "'${IMG_DIR}'/$f";
        }
    }' $RESULT_XML
fi

date
end_ts=`date +"%s"`
echo "elapse="$(($end_ts-$start_ts))
