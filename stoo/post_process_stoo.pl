#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker qw(get_encoding_from_config);


sub main
{
	my $second_page_url = "";

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!<a href='(http://[^']+)'[^>]*><img src='http://cwstatic\.asiae\.co\.kr/images/cartoon/btn_s\.gif'/>!) {
			$second_page_url = $1;
		} elsif ($line =~ m!<a href='(http://stoo.asiae.co.kr/cartoon/view.htm[^"]*)'>2페이지</a>!) {
			$second_page_url = $1;
		} elsif ($line =~ m!<img src='(http://cwcontent[^']+)'.*/>!) {
			print "<img src='" . $1 . "' width='100%'/>\n";
		}
	}

	if ($second_page_url ne "") {
		my $encoding = get_encoding_from_config();

		my $cmd = qq(wget.sh "$second_page_url" $encoding | extract_element.py extraction);
		#print $cmd . "\n";
		my $result = `$cmd`;
		if ($CHILD_ERROR == 0) {
			for my $line (split /\n/, $result) {
				if ($line =~ m!<img\s*[^>]*src=(?:'|")(http://cwcontent[^'"]+)(?:'|").*/>!) {
					print "<img src='" . $1 . "' width='100%'/>\n";
				}
			}
		}
	}
}


main();
