#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use FeedMaker;


sub get_config
{
    my $config = ();
    my $config_file = "conf.xml";
    if (not FeedMaker::read_config($config_file, \$config)) {
        confess "Error: can't read configuration!, ";
        return -1;
    }
    my $extraction_config = $config->{"collection"};
    if (not defined $extraction_config) {
        confess "Error: can't read extraction config!, ";
        return -1;
    }
    my $element_list = $extraction_config->{"element_list"};
    my $element_class = $element_list->{"element_class"};
    if (not defined $element_class) {
        $element_class = "";
    }
    my $element_id = $element_list->{"element_id"};
    if (not defined $element_id) {
        $element_id = "";
    }
    my $encoding = $extraction_config->{"encoding"};
    if (not defined $encoding) {
        $encoding = "utf8";
    }

    return $encoding;
}


sub main
{
	my $link = "";
	my $title = "";

	my $encoding = get_config();

	# 오래된 html 파일 지움
	my $cmd = qq(find newlist -name "*.html" -mtime +7 -exec rm -f "{}" \\;);
	my $result = qx($cmd);

	while (my $line = <STDIN>) {
		if ($line =~ m!<a class="p" href="(http://www.wowtv.co.kr/newscenter/webtoon/view\.asp[^"]+)"><span class="tit">(.+)</span>.*</a>!) {
			$link = $1;
			$title = $2;

			# 링크에 들어가서 1화를 찾아서 해당 링크 주소를 확인
			my $html_file = "newlist/" . FeedMaker::get_md5_name($link) . ".html";
			my $cmd = qq([ -e "${html_file}" -a -s "${html_file}" ] || wget.sh --download "$link" ${html_file}; iconv -c -f $encoding -t utf8 ${html_file} | grep '<option value="[0-9][0-9]*">1[^0-9]' | head -1);
			#print $cmd . "\n";
			my $result = qx($cmd);
			if ($ERRNO != 0) {
				print $ERRNO;
			}
			#print $result;
			if ($result =~ m!<option value="(\d+)">1화!) {
				$link = "http://www.wowtv.co.kr/funfun/fun/webtoon/view.asp?webtoonIdx=" . $1;
				print "$link\t$title\n";
			}
		}
	}
}


main();
