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
		if ($line =~ m!<a href="(http://news.khan.co.kr/kh_news/khan_art_view.html\?artid=(\d+)&amp;code=\d+)" title="\[장도리\]">!) {
			$link = $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
		} elsif ($line =~ m!<strong>\[장도리\]</strong>!) {
			if ($title =~ m!^(\d{4,4})(\d{2,2})(\d{2,2})!) {
				my $new_title = "$1년 $2월 $3일";	
				print "$link\t$new_title\n";
				last;
			}
		}
	}
}


main();
