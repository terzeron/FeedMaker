#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use FeedMaker;


sub main
{
	my $link = "";
	my $title = "";
	my $state = 0;

	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!<a href="#" onclick="javascript:fncChkAdult\((\d+),\s?(\d+)\)!) {
				$link = "http://webtoon.olleh.com/toon/timesDetail.kt?webtoonseq=$1&timesseq=$2";
				$link =~ s!&amp;!&!g;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<span class="tit">(.+)</span>!) {
				$title = $1;
				$title =~ s!\&\#39;!'!g;
				print "$link\t$title\n";
				$state = 0;
			}
		}
	}
}


main();
