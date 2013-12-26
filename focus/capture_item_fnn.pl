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
		if ($line =~ m!<td align="left">\s*<a href="/([^"]+)">(\[\d+\]\s*[^<]*)\s*</a>\s*</td>!) {
 		    $link = $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			$link =~ s!&week(day)?=\w\w\w!!g;
			$link = "http://www.focus.co.kr/" . $link;
			print "$link\t$title\n";
		}
	}
}


main();
