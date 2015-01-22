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
		if ($line =~ m!<a href="/(cartoon/list.htm\?sec=\d+)"!) {
			$link = $1;
			$link =~ s!&amp;!&!g;
			$link = "http://stoo.asiae.co.kr/" . $link;
		} elsif ($line =~ m!<dt class="desc">([^<]+)</dt>!) {
			$title = $1;
			print "$link\t$title\n";
		}
	}
}


main();
