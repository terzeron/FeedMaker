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
		if ($line =~ m!<dt class="dt_title"><a href="/(news/articleView.html[^"]+)"[^>]*>(.*)</a></dt>!) {
 		    $link = $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			$link =~ s!&week(day)?=\w\w\w!!g;
			$link = "http://www.sisainlive.com/" . $link;
			print "$link\t$title\n";
		}
	}
}


main();
