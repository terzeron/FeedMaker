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

	while (my $line = <STDIN>) {
		if ($line =~ m!<a href="/((?:webtoon|challenge|bestChallenge)/detail.nhn[^"]+no=(\d+)[^"]+)"[^>]*>(.+)</a>!) {
			$link = $1;
			$title = sprintf("%04d. %s", $2, $3);
			$link =~ s!&amp;!&!g;
			$link =~ s!&week(day)?=\w\w\w!!g;
			$link = "http://comic.naver.com/" . $link;
			print "$link\t$title\n";
		}
	}
}


main();
