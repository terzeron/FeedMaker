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
	my $icon = "";
	my $state = 0;


	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!<p class="img2"><a href="./(comicDetail.htm\?nComicSeq=\d+)">!) {
				$link = "http://comic.mt.co.kr/" . $1;
				$link =~ s!&amp;!&!g;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<p class="title"><strong>(.+)</strong></p>!) {
				$title = $1;
				print "$link\t$title\t$icon\n";
				$state = 0;
			}
		}
	}
}


main();
