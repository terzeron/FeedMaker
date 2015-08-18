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
			if ($line =~ m!<span class="l_link" data-href="(/home/\d+)\?[^"]+">!) {
				$link = $1;
				$num = $2;
				$link =~ s!&amp;!&!g;
				$link =~ s!&week(day)?=\w\w\w!!g;
				$link =~ s!&listPage=\d+!!g;
				$link = "http://page.kakao.com/" . $link;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<strong class="title" style="word-break:break-all">!) {
				$state = 2;
			}
		} elsif ($state == 2) {
			if ($line =~ m!<img!){
				next;
			}
			if ($line =~ m!^\s*(\S.*\S)\s*$!) {
				$title = $1;
				print "$link\t$title\n";
				$state = 0;
			}
		}
	}
}


main();
