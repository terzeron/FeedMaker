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

	# <li><a href="http://www.informatik.uni-trier.de/~ley/db/journals/cacm/cacm56.html">Volume 56, 2013</a></li>

	while (my $line = <STDIN>) {
		if ($line =~ m!</span>\s*([^<]+)\s*\[<a href="(http://[^"]+)"> contents </a>\]!) {
			$title = $1;
			$link = $2;
			$link =~ s!&amp;!&!g;
			print "$link\t$title\n";
		}
		if ($line =~ m!<li><a href="(http://[^"]+)">(Volume[^<]+)</a></li>!) {
			$link = $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			print "$link\t$title\n";
		}
	}
}


main();
