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
			if ($line =~ m!<a class="wtl_toon\s*" href="/(webtoon/list.php\?btno=\d+)">!) {
				$link = $1;
				$link = "http://comics.nate.com/" . $link;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<span class="wtl_title">(.+)</span>!) {
				$title = $1;
				print "$link\t$title\n";
				$state = 0;
			}
		}
	}
}


main();
