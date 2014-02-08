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
	my $num = "";
	my $state = 0;

	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!<a href="/((?:webtoon|challenge|bestChallenge)/detail\.nhn[^"]+no=(\d+)[^"]+)"[^>]*>!) {
				$link = $1;
				$num = $2;
				$link =~ s!&amp;!&!g;
				$link =~ s!&week(day)?=\w\w\w!!g;
				$link =~ s!&listPage=\d+!!g;
				$link = "http://m.comic.naver.com/" . $link;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<span class="toon_name"><span>(.*)</span></span>!) {
				$title = sprintf("%04d. %s", $num, $1);
				print "$link\t$title\n";
				$state = 0;
			}
		}
	}
}


main();
