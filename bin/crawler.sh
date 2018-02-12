if [ $# -lt 1 ]; then
	echo "Usage: $0 [ <option> ... <option> ] <url>"
	echo "Options"
	echo "	--spider:	no download, just trying"
	echo "	--download: download as a file, instead of stdout"
	echo "	--render-js: phantomjs rendering"
	echo "	--ua <user agent string>"
	echo "	--referer <referer>"
	echo "	--uncompress-gzip: uncompress content with gzip"
    echo "  --header <header string>: specify header string"
	exit 0
fi

spider_opt=""
#ua_opt="--user-agent 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.37 (KHTML, like Gecko) Chrome/31.0.1650.58 Safari/537.37'"
referer_opt=""
render_js=false
uncompress_gzip=false
header_opt=""

encoding=$(python -c 'import feedmakerutil as fmu; encoding = fmu.get_config_value(fmu.get_config_node(fmu.read_config(), "collection"), "encoding"); print(encoding if encoding else "utf8")')
#cookie_opt="--cookie-jar cookie.txt"
timeout_opt="--connect-timeout 10"
cert_opt="--insecure"

OPTS=`/usr/local/bin/getopt -o v --long spider,render-js,uncompress-gzip,download:,ua:,referer:,header: -- "$@"`

eval set -- "$OPTS"

while :; do
	case "$1" in
		-v) verbose_opt="-v"; shift;;
		--spider) spider_opt="--head"; shift;;
		--render-js) render_js=true; shift;;
        --uncompress-gzip) uncompress_gzip=true; shift;;
		--download) download_file="$2"; shift 2;;
		--ua) ua_opt="--user-agent '$2'"; shift 2;;
		--referer) referer_opt="--referer '$2'"; shift 2;;
        --header) header_opt="$header_opt --header '$2'"; shift 2;;
		--) shift; break;
	esac
done

url="'$1'"

if [ "$render_js" == true ]; then
	cmd="phantomjs $FEED_MAKER_HOME/bin/render_js.js $url | grep -v '^Unable to access the page'"
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

