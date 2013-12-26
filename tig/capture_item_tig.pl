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
		if ($line =~ m!<a href="/(board/view.php\?[^"]+)">(.+)</a>!) {
 	    	$link = $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			$link = "http://www.thisisgame.com/" . $link;
			print "$link\t$title\n";
		}
	}
}


main();
