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
		if ($line =~ m!<p class="title"><a href="/(arti/cartoon/hanicartoon/\d+\.html)">(.*)</a></p>!) {
			$link = "http://www.hani.co.kr/" . $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			print "$link\t$title\n";
		}
	}
}


main();
