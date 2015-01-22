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
		if ($line =~ m!<a href="([^"]+)"[^>]*>([^<]*) 이동진의.*</a>!) {
			$link = $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			$link = "http://program.interest.me" . $link;
			print "$link\t$title\n";
		}
	}
}


main();
