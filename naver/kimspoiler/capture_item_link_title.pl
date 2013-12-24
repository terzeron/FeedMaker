#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;


sub main
{
	my $link = "";
	my $title = "";
	my $state = 0;

	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!<a href="(/main/hotissue/read\.nhn\?mid=hot&amp;sid1=\d+&amp;cid=\d+&amp;iid=\d+&amp;oid=\d+&amp;aid=\d+&amp;ptype=\d+)">!) {
				$link = $1;
				$link =~ s!&amp;!&!g;
				$link = "http://news.naver.com/" . $link;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!^\s*\[김혜리\s*칼럼\]\s*(.+)\s*$!) {
				$title = $1;
				print "$link\t$title\n";
				$state = 0;
			}
		}
	}
}


main();
