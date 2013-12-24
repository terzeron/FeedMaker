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
		if ($line =~ m!<li(?: class="first")?><a href="(\?cid=[^"]+)"><img alt="([^"]+)"!) {
			$link = "http://sports.donga.com/cartoon" . $1;
			$title = $2;
			print "$link\t$title\n";
		}
	}
}


main();
