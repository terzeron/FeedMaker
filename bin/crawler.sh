if [ $# -lt 1 ]; then
	echo "Usage: $0 [ <option> ... <option> ] <url>"
	echo "Options"
	echo "	--spider:	no download, just trying"
	echo "	--download: download as a file, instead of stdout"
	echo "	--render-js: phantomjs rendering"
	echo "	--ua <user agent string>"
	echo "	--referer <referer>"
	echo "	--header-gzip: set request header with 'Accept-Encoding: gzip'"
	echo "	--uncompress-gzip: uncompress content with gzip"
	exit 0
fi

default_spider_opt=""
default_ua_opt="--user-agent 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.37 (KHTML, like Gecko) Chrome/31.0.1650.58 Safari/537.37'"
default_referer_opt=""
default_render_js=false
default_uncompress_gzip=false
default_header_opt=""

spider_opt=$default_spider_opt
ua_opt=$default_ua_opt
referer_opt=$default_referer_opt
render_js=$default_render_js
uncompress_gzip=$default_uncompress_gzip
header_opt=$default_header_opt

encoding=$(python -c 'import feedmakerutil as fmu; encoding = fmu.get_config_value(fmu.get_config_node(fmu.read_config(), "collection"), "encoding"); print(encoding if encoding else "utf-8")')
cookie_opt="--cookie-jar cookie.txt"
timeout_opt="--connect-timeout 5"
cert_opt="--insecure"

OPTS=`/usr/local/bin/getopt -o v --long spider,download:,render-js,uncompress-gzip,ua:,referer:,header-gzip -- "$@"`

eval set -- "$OPTS"

while :; do
	case "$1" in
		-v) verbose_opt="-v"; shift;;
		--spider) spider_opt="--head"; shift;;
		--download) download_file="$2"; shift 2;;
		--render-js) render_js=true; shift;;
		--ua) ua_opt="--user-agent '$2'"; shift 2;;
		--referer) referer_opt="--referer '$2'"; shift 2;;
		--header-gzip) header_opt="--header 'Accept-Encoding: gzip'"; shift;;
		--) shift; break;
	esac
done

url="'$1'"

if [ "$render_js" == true ]; then
	cmd="phantomjs $FEED_MAKER_HOME/bin/render_js.js $url"
else
	cmd="curl --silent --location $header_opt $timeout_opt $ua_opt $cert_opt $cookie_opt $referer_opt $url"
fi

if [ "${spider_opt}" != "" ]; then
    cmd="$cmd > /dev/null"
elif [ "${download_file}" != "" ]; then
	cmd="$cmd > '$download_file'"
fi

# post processing

if [ "$uncompress_gzip" == true ]; then
    cmd="$cmd | gzip -cd"
fi

if [ "${encoding}" != "utf8" ]; then
	cmd="$cmd | iconv -c -f $encoding -t utf8"
fi
    
if [ "$verbose_opt" == "-v" ]; then
	echo "$cmd"
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

