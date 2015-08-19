if [ $# -lt 1 ]; then
	echo "Usage: $0 [ <option> ... <option> ] <url>"
	echo "	Options"
	echo "		--try:	no download, just trying"
	echo "		--download: download as a file, instead of stdout"
	echo "		--render-js: phantomjs rendering"
	echo "		--ua <user agent string>"
	echo "		--referer <referer>"
	exit 0
fi

default_spider_opt=""
default_ua_opt="-U 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.37 (KHTML, like Gecko) Chrome/31.0.1650.58 Safari/537.37'"
default_referer_opt=""
default_render_js=false

spider_opt=${default_spider_opt}
ua_opt=${default_ua_opt}
referer_opt=${default_referer_opt}
render_js=${default_render_js}

encoding=$(perl -e 'use FeedMaker qw(get_encoding_from_config); print get_encoding_from_config();')
cookie_opt="--keep-session-cookies --load-cookies cookie.txt --save-cookies cookie.txt"
timeout_opt="--timeout=5"
cert_opt="--no-check-certificate"

OPTS=`/usr/local/bin/getopt -o v --long spider,download:,render-js,ua:,referer: -- "$@"`

eval set -- "$OPTS"

while :; do
	case "$1" in
		-v) verbose_opt="-v"; shift;;
		--spider) spider_opt="--spider"; shift;;
		--download) download_file="$2"; shift 2;;
		--render-js) render_js=true; shift;;
		--ua) ua_opt="-U '$2'"; shift 2;;
		--referer) referer_opt="--referer='$2'"; shift 2;;
		--) shift; break;
	esac
done

url="'$1'"

if [ "${render_js}" == true ]; then
	cmd="phantomjs ../../bin/render_js.js ${url}"
else
	cmd="wget -q -O - ${timeout_opt} ${ua_opt} ${cert_opt} ${cookie_opt} ${referer_opt} ${url}"
fi

if [ "${encoding}" != "utf8" ]; then
	cmd="${cmd} | iconv -c -f ${encoding} -t utf8"
fi

if [ "${download_file}" != "" ]; then
	cmd="${cmd} > \"${download_file}\""
fi

if [ "${verbose_opt}" == "-v" ]; then
	echo "${cmd}"
fi

eval "${cmd}"

exit_status=$?
if [ "$download_file" != "" ]; then
	if [ "$exit_status" -eq 0 ]; then
		touch "$download_file"
	else 
		rm -f "$download_file"
	fi
fi
exit $exit_status

