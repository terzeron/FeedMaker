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
	my @result = ();
	
	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!<a\s+class="[^"]+"\s+href=\"/(todayMusic/index\.nhn[^\"]+)\"[^>]*>!) {
				$link = "http://music.naver.com/" . $1;
				$link =~ s!&amp;!&!g;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<span\s+class="[^"]+"\s+title=\"[^\"]+\"[^>]*>([^<]+)</span>!) {
				$title = $1;
				unshift @result, "$link\t$title";
				$state = 0;
			}
		}
	}

	my $count = 0;
	for my $item (@result) {
		print "$item\n";
		$count++;
		if ($count >= 7) {
			last;
		}
	}
}


main();
