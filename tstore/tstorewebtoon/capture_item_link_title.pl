#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use FeedMaker qw(get_encoding_from_config);


sub get_list_page_link
{
	my $link = shift;
	my $encoding = shift;
	my $first_article_link = "";

	# 링크에 들어가서 1화를 찾아서 해당 링크 주소를 확인
	my $html_file = "newlist/" . FeedMaker::get_md5_name($link) . ".html";
	my $cmd = qq{[ -e "${html_file}" -a -s "${html_file}" ] || wget.sh --download "$link" ${html_file}};
	my $result = qx($cmd);
	if ($ERRNO != 0) {
		confess "Error: can't get list page from '$link', $ERRNO\n";
		exit(-1);
	}

	#print "html_file: $html_file\n";
	open(my $infp, $html_file);
	if ($infp) {
		while (my $line = <$infp>) {
			# <div class="btnFirview"><a href="javascript:goStatsContentsDetail('/webtoon/webtoonDetail.omp?prodId=H900723573&menuId=DP26001','49', '', 'H900723573','');">첫회보기</a></div>
			if ($line =~ m!
							  <div
							  \s*
							  class="btnFirview">
							  <a
							  \s*
							  href="javascript:goStatsContentsDetail\('
							  (/webtoon/webtoonDetail\.omp\?prodId=[^']+)
							  '[^>]*
							  >
							  [^<]*
							  </a>
							  </div>
						  !x) {
				$first_article_link = $1;
				last;
			}
		}
	}
	close($infp);
	return $first_article_link;
}


sub main
{
	my $link = "";
	my $title = "";
	my $state = 0;
	my @result_arr = ();

	my $encoding = get_encoding_from_config();

	my $cmd = qq(find newlist -name "*.html" -mtime +7 -exec rm -f "{}" \\;);
	my $result = qx($cmd);

	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!
							  <a
							  [^>]*
							  goInnerUrlDetail\(
							  \\
							  '
							  (
								  /webtoon/webtoonList[^']+
							  )
							  \\
							  '
						  !gx) {
				$link = "http://m.tstore.co.kr/mobilepoc" . $1;
				$link =~ s!&amp;!&!g;
				$state = 1;
			} 
		} elsif ($state == 1) {
			if ($line =~ m!
							  <dt>
							  (.+)
							  </dt>
						  !gx) {
				$title = $1;
				push @result_arr, "$link\t$title";
				$state = 0;
			}
		}
	}

	my $i = 0;
	foreach my $item (@result_arr) {
		print $item . "\n";
		$i++;
		if ($i >= 5) {
			last;
		}
	}
}


main();
