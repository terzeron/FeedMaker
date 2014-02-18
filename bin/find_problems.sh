if [ "${FEED_MAKER_HOME}" == "" ]; then
	echo "FEED_MAKER_HOME is not set"
	exit -1
fi
work_dir=${FEED_MAKER_HOME}
public_html_dir=/Users/terzeron/public_html/xml

cd ${work_dir}

echo
echo "===== check the validity of configuration file ====="

echo "--- the number of <list_url> element ---"
find . -name conf.xml -exec grep -c "<list_url>" "{}" \; -print | perl -ne 'if (/^(\d+)$/ and $1 > 1) { $count = $1; } if (/^(\..+\.xml)$/) { if ($count > 1) { s/\/conf\.xml//; print $count . "\t" . $_; $count = 0; } }' | sort -n

echo "--- the number of occurrence of each element ---"
find . -name conf.xml -exec perl -ne 'while (/\<(\w+)\>/g) { if ($1 !~ /encoding|collection|extraction|copyright|configuration|element_list|description|language|link|list_url_list|rss|title|list_url|element_class|element_id|element_path|feed_url|generator/) { print $1 . "\n"; } }' "{}" \; |sort | uniq -c | sort -n | perl -ne 'if (/^\s*(\d+)\s+/) { print; }'

echo "--- spaces instead of tab ---"
find . -name conf.xml -exec grep -l "	 " "{}" \;


echo 
echo "===== check the size and time of result file ====="

echo "--- old xml files in ${public_html_dir} ---"
find ${public_html_dir} -name "*.xml" -mtime +10d -print

echo "--- too small html file ---"
find . -name "*.html" -maxdepth 3 -size -50c -print | grep -v warfareafterschool

#echo "--- html files containing iframe element ---"
#find . -name "*.html" -exec grep -l "<iframe" "{}" \; | cut -d/ -f3 | uniq -c | sort -n

echo "--- top 10 in running time ---"
find . -name run.log | xargs grep elapse= | sort -t= -k2 -n | tail -10

echo 
echo "===== check the incremental feeding ====="

echo "--- completed feeds ---"
find . -name conf.xml -exec grep -l "<is_completed>true" "{}" \; 

echo "--- start_idx vs # of items ---"
for f in $(find . -name conf.xml -exec grep -l "<is_completed>true" "{}" \; | xargs -L1 dirname); do [ -d "$f" ] && (cd $f; idx=$(cut -f1 start_idx.txt); cnt=$(sort -u newlist/*.txt | wc -l | tr -d ' '); if [ "$idx" -gt "$cnt" ]; then echo "$f idx=$idx count=$cnt"; fi); done

echo
echo "===== check the garbage feeds ====="
feedmaker_file="log/feedmaker.txt"
find */ -maxdepth 2 -name "*.xml" \! -name conf.xml -exec basename "{}" \; | perl -pe 's/\.xml//; s/\\\././g' | sort -u > $feedmaker_file
period_file_list=""
for i in {1..14}; do
	period_file_list="${period_file_list} /Applications/MAMP/logs/apache_access.log.$(date -v-${i}d +'%Y%m%d')"
done
feed_access_file="log/feed_access.txt"
echo "--- $feed_access_file ---"
perl -e '
my %name_date_map = ();
my %month_map = ("Jan"=>"01", "Feb"=>"02", "Mar"=>"03", "Apr"=>"04", "May"=>"05", "Jun"=>"06", "Jul"=>"07", "Aug"=>"08", "Sep"=>"09", "Oct"=>"10", "Nov"=>"11", "Dec"=>"12"); 
while (my $line = <>) {
	if ($line =~ m!\[(\d+)/(\w+)/(\d+):\d+:\d+:\d+ \+\d+\] "GET /img/1x1\.jpg\?feed=([\w\.\_]+)\.xml\S* HTTP\S+" (\d+) (?:\d+|-) "[^"]*" "[^"]*"!) {
		$name_date_map{$4} = "$3$month_map{$2}$1\t$5";
	}
} 
foreach my $name (sort { $name_date_map{$b} <=> $name_date_map{$a} } keys %name_date_map) {
	my ($date, $status) = split /\t/, $name_date_map{$name};
	print "$date\t$name\t$status\n";
}' $period_file_list > $feed_access_file
wc -l $feed_access_file
echo "--- check the existence of requested feed ---"
perl -e '
use HTTP::Status qw(status_message);
my %feed_map = ();
open(FM, $ARGV[0]);
while (my $line = <FM>) {
	if ($line =~ m!(.+)!) {	
		$feed_map{$1} = $1;
	}
}
close(FM);
open(LASTREQ, $ARGV[1]);
while (my $line = <LASTREQ>) { 
	if ($line =~ m!(\d+)\t([\w\.\_]+)\t(\d+)!) {
		my $date = $1;
		my $name = $2;
		my $status = $3;
		my $exist = "";
		if (exists $feed_map{$name} or $name eq "index") {
			$exist = "o";
		} else {
			$exist = "x";
		}
		if ($exist eq "x" and ($status == 200 or $status == 304)) { 
			$color = 31;
			printf("%s %-25s %s \033[1;%dm%d\033[0m %s\n", $date, $name, $exist, $color, $status, status_message($status));
		} elsif ($exist eq "o" and ($status == 404 or $status == 410)) {
			$color = 34;
			printf("%s %-25s %s \033[1;%dm%d\033[0m %s\n", $date, $name, $exist, $color, $status, status_message($status));
		} else {
			$color = 39;
		}
	}
}
close(LASTREQ);' $feedmaker_file $feed_access_file
echo "--- false path (${public_html_dir}) of recent days ---"
perl -e '
use HTTP::Status qw(status_message); 
use DateTime; 
my $now = DateTime->now();
my $format = "%d/%b/%Y";
my $today = $now->strftime($format);
%name_status_map = ();
while (<>) { 
	if (m!\[$today:\d+:\d+:\d+ \+\d+\] "GET /xml/(.+)\.xml HTTP\S+" (\d+)!s) { 
		my $name = $1;
		my $status = $2;
		$name_status_map{$name} = $status;
	}
}
foreach my $name (keys %name_status_map) {
	my $status = $name_status_map{$name};
	if ($status eq "200") { 
		$color = 34;
	} elsif ($status eq "304") {
		$color = 31;
	} elsif ($status eq "404") {
		$color = 32;
	} elsif ($status eq "410") {
		$color = 39;
	}
	printf("%-25s \033[1;%dm%d\033[0m %s\n", $name, $color, $status, status_message($status)); 
}' $period_file_list | sort -u


echo
echo "===== inconsistent registration ====="
feedly_file="log/feedly.txt"
public_html_xml_file="log/public_html_xml.txt"
htaccess1_xml_file="log/htaccess1_xml.txt"
htaccess2_xml_file="log/htaccess2_xml.txt"
find ${public_html_dir} -name "*.xml" -exec basename "{}" \; | perl -pe 's/\.xml//; s/\\\././g' | sort -u > $public_html_xml_file
perl -ne 'if (m!RewriteRule\s+\^(\S*)\\\.xml\$?\s+xml/(\S+)\\\.xml!) { print $1 . "\n"; }' ~/public_html/.htaccess | perl -pe 's/\.xml//; s/\\\././g' | sort -u > $htaccess1_xml_file
perl -ne 'if (m!RewriteRule\s+\^(\S*)\\\.xml\$?\s+xml/(\S+)\\\.xml!) { print $2 . "\n"; }' ~/public_html/.htaccess | perl -pe 's/\.xml//; s/\\\././g' | sort -u > $htaccess2_xml_file
perl -ne 'my ($date, $feed, $status) = split /\t/, $_; print $feed . "\n";' $feed_access_file | sort -u > $feedly_file
echo "--- feedly(http request) vs. .htaccess ---"
/usr/local/bin/colordiff $feedly_file $htaccess2_xml_file
echo "--- .htaccess vs. ${public_html_dir} ---"
/usr/local/bin/colordiff $htaccess2_xml_file $public_html_xml_file 
echo "--- ${public_html_dir} vs. feedmaker/*/*/*.xml ---"
/usr/local/bin/colordiff $public_html_xml_file $feedmaker_file
#rm -f $feedly_file $htaccess_xml_file $public_html_xml_file $feedmaker_file
