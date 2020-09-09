#!/bin/bash

if [ "$FEED_MAKER_WORK_DIR" == "" -o "$FEED_MAKER_WWW_FEEDS_DIR" == "" ]; then
    echo "You should declare FEED_MAKER_WORK_DIR and FEED_MAKER_WWW_FEEDS_DIR."
    exit -1
fi
work_dir=$FEED_MAKER_WORK_DIR
public_html_dir=$FEED_MAKER_WWW_FEEDS_DIR

cd $work_dir

echo
echo "===== check the validity of configuration file ====="

echo "--- the number of <list_url> element ---"
find . -name conf.xml -print0 | xargs -0 grep -c "<list_url>" | grep -v "/_" | perl -ne 'if (/^(\d+)$/ and $1 > 1) { $count = $1; } if (/^(\..+\.xml)$/) { if ($count > 1) { s/\/conf\.xml//; print $count . "\t" . $_; $count = 0; } }' | sort -n

echo "--- the number of occurrence of each element ---"
find . -name conf.xml | xargs| grep -v "/_" | perl -ne 'while (/\<(\w+)\>/g) { if ($1 !~ /encoding|collection|extraction|copyright|configuration|element_list|description|language|link|list_url_list|rss|title|list_url|element_class|element_id|element_path|feed_url|generator/) { print $1 . "\n"; } }' | sort | uniq -c | sort -n | perl -ne 'if (/^\s*(\d+)\s+/) { print; }'

echo "--- should use spaces instead of tab ---"
find . -name conf.xml -exec grep -l "	" "{}" \;


echo 
echo "===== check the size and time of result file ====="

echo "--- old xml files in ${public_html_dir} ---"
find ${public_html_dir} -name "*.xml" -mtime +240 -print

echo "--- too small html file ---"
find . -maxdepth 4 -name "*.html" \( -size +0c -a -size -50c \) -print

#echo "--- html files containing iframe element ---"
#find . -name "*.html" -exec grep -l "<iframe" "{}" \; | cut -d/ -f3 | uniq -c | sort -n

#echo "--- top 10 in running time ---"
#find . -name run.log | xargs grep elapse= | sort -t= -k2 -n | tail -10

echo 
echo "===== check the image tag (1x1.jpg) ====="

echo "--- corrupted html files without image tag ---"
find . -name "*.html" -print0 | xargs -0 -I % perl -e '$count = 0; $contents_count = 0; while (<ARGV>) { if (/1x1.jpg/) { $count++; } if (/<(img|div)/) { $contents_count++; } } if ($contents_count > 0 && $count < 1) { print "$ARGV $count $contents_count\n"; }' %

echo "--- corrupted html files with many image tags ---"
find . -name "*.html" -print0 | xargs -0 -I % perl -e '$count = 0; $contents_count = 0; while (<ARGV>) { if (/1x1.jpg/) { $count++; } if (/<(img|div)/) { $contents_count++; } } if ($contents_count > 0 && $count > 1) { print "$ARGV $count $contents_count\n"; }' %

echo "--- html files with image not found ---"
find . -name "*.html" -print0 | xargs -0 -I % grep -l image-not-found.png % | cut -d'/' -f2-5 | sort | uniq -c | sort -rn

echo 
echo "===== check the incremental feeding ====="

#echo "--- completed feeds ---"
#find . -name conf.xml -exec grep -l "<is_completed>true" "{}" \;

echo "--- start_idx vs # of items ---"
for f in $(find . -name conf.xml -exec grep -l "<is_completed>true" "{}" \; -print0 | xargs -0 -I % dirname % | grep -v /_); do 
    if [ -d "$f" ]; then
        (
            cd $f;
            idx=$(cut -f1 start_idx.txt);
            cnt=$(sort -u newlist/*.txt | wc -l | tr -d ' ');
            unit_size=$(xmllint --xpath '//unit_size_per_day/text()' conf.xml);
            remainder=$((cnt - (idx + 4)));
            days=$(echo "$remainder / $unit_size" | bc);
            echo "$f: "$((idx + 4))" / $cnt = "$(((idx + 4) * 100 / cnt))"%, $unit_size articles/day, "$(date +"%Y-%m-%d" -d "$days days"); 
        )
    fi
done | sort -k6 -rn

echo
echo "===== check the garbage feeds ====="
feedmaker_file=$FEED_MAKER_WORK_DIR"/logs/feedmaker.txt"
find */ -maxdepth 2 -name "*.xml" \! \( -name conf.xml -o -name _conf.xml -o  -name "*.conf.xml" \) | grep -v /_ | xargs -I % basename % | perl -pe 's/\.xml//; s/\\\././g' | sort -u > $feedmaker_file
period_file_list=""
for i in {0..30}; do
    period_file_list="${period_file_list} $HOME/apps/logs/access.log.$(date +'%y%m%d' -d $i' days ago')"
done
feed_access_file=$FEED_MAKER_WORK_DIR"/logs/feed_access.txt"
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

echo "--- false path (${public_html_dir}) of recent days ---"
find_requests_to_false_path.py $period_file_list


echo
echo "===== inconsistent registration ====="
make_feed_status.py > $FEED_MAKER_WWW_ADMIN_DIR/status.json

