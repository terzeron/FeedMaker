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
			if ($line =~ m!<a href="timesDetail\.kt\?timesseq=\d+[^"]*webtoonseq=(\d+)[^"]*"[^>]*>!) {
				$link = "http://webtoon.olleh.com/toon/timesList.kt?webtoonseq=" . $1;
				$link =~ s!&amp;!&!g;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<span class="nm">(.+)</span>!) {
				$title = $1;
				$title =~ s!\&\#39;!'!g;
				$state = 2;
			}
		} elsif ($state == 2) {
			if ($line =~ m!<span class="dd_author">(.+)</span>!) {
				$title .= " by " . $1;
				print "$link\t$title\n";
				$state = 0;
			}
		}
	}
}


main();
