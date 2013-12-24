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
			if ($line =~ m!<a href="./(\?nOrder=view&amp;nStatus=&amp;nViewSeq=\d+)&amp;nPage=\d*">!) {
				$link = $1;
				$link =~ s!&amp;!&!g;
				$link = "http://mcomic.mt.co.kr/kakaotalk/" . $link;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<span class="subtitle"><strong>(\d+화)</strong> \|? <strong>(.*)</strong></span>!) {
				$title = $1 . " " . $2;
				print "$link\t$title\n";
				$state = 0;
			}
		}
	}
}


main();
