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
		if ($line =~ m!<dt class="desc"><a href="/(cartoon/ctlist.htm\?sc1=cartoon&amp;sc2=ing&amp;sc3=\d+)"[^>]*><em>([^<]+)(?:<img.*>)?</em></a>!) {
			$link = $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			$link = "http://stoo.asiae.co.kr/" . $link;
			print "$link\t$title\n";
		}
	}
}


main();
