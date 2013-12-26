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
		if ($line =~ m!<a href="(vx2.php[^"]+)">(.*)\s*(?:\[\d+\])?</a>!) {
			$link = "http://www.slrclub.com/bbs/" . $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			$link =~ s!&page=\d+!!g;
			$title =~ s!\s+! !g;
			print "$link\t$title\n";
		}
	}
}


main();
