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
		if ($line =~ m!<h3 class="title"><a href="/(episode/\d+)">([^<]+)</a></h3>!) {
 		    $link = "http://tapastic.com/" . $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			$link =~ s!&week(day)?=\w\w\w!!g;
			print "$link\t$title\n";
		}
	}
}


main();
