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
	my $icon = "";
	my $state = 0;

	while (my $line = <STDIN>) {
		if ($line =~ m!<a href=\"/(news/view/idx/\d+/mag_id/\d+)\"[^>]*>\[.*\]\s*(.+)</a>!) {
			$link = "http://www.cine21.com/" . $1;
			$link =~ s!&amp;!&!g;
			$title = $2;
			print "$link\t$title\n";
		}
	}
}


main();
