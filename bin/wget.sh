if [ $# -lt 2 ]; then
	echo "Usage: $0 [ --try ] [ --download ] [ --render_js ] <url> [ <encoding> ]"
	exit 0
fi

printout_opt="-q"
ua_opt="-U 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.37 (KHTML, like Gecko) Chrome/31.0.1650.58 Safari/537.37'"
cookie_opt="--keep-session-cookies --load-cookies cookie.txt --save-cookies cookie.txt"
cert_opt="--no-check-certificate"

if [ "$1" == "-v" ]; then
	shift
	printout_opt="-v"
fi

if [ "$1" == "--try" ]; then
	shift
	if [ "${printout_opt}" == "-v" ]; then
		echo "# wget ${printout_opt} --spider \"${ua_opt}\" ${cert_opt} ${cookie_opt} \"$1\""
	fi
	wget ${printout_opt} --spider "${ua_opt}" ${cert_opt} ${cookie_opt} "$1"
elif [ "$1" == "--download" ]; then
	shift
	if [ -n "$3" ]; then
		referer_opt="--referer='$3'"
	fi
	if [ "${printout_opt}" == "-v" ]; then
		echo "# wget ${printout_opt} \"${ua_opt}\" ${cert_opt} ${cookie_opt} ${referer_opt} -O \"$2\" \"$1\""
	fi
	wget ${printout_opt} "${ua_opt}" ${cert_opt} ${cookie_opt} ${referer_opt} -O "$2" "$1" 
	exit_status=$?
	if [ $exit_status -eq 0 ]; then
		touch "$2"
	else 
		rm -f "$2"
	fi
	exit $exit_status
elif [ "$1" == "--render_js" ]; then
	shift
	if [ "$2" == "utf8" ]; then
		echo "# phantomjs ../../bin/render_js.js \"$1\""
		phantomjs ../../bin/render_js.js "$1"
	else
		phantomjs ../../bin/render_js.js "$1" | iconv -c -f $2 -t utf8
	fi
else 
	if [ "$2" == "utf8" ]; then
		if [ "${printout_opt}" == "-v" ]; then
			echo "# wget ${printout_opt} -O - \"${ua_opt}\" ${cert_opt} ${cookie_opt} \"$1\""
		fi
		wget ${printout_opt} -O - "${ua_opt}" ${cert_opt} ${cookie_opt} "$1"
	else
		if [ "${printout_opt}" == "-v" ]; then
			echo "# wget ${printout_opt} -O - \"${ua_opt}\" ${cert_opt} ${cookie_opt} \"$1\" | iconv -c -f $2 -t utf8"
		fi
		wget ${printout_opt} -O - "${ua_opt}" ${cert_opt} ${cookie_opt} "$1" | iconv -c -f $2 -t utf8
	fi
fi
