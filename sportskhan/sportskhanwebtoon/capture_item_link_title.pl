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
		if ($line =~ m!<li(?: class="[^"]+")?><a href="(http://sports.khan.co.kr/[^"]+)">([^<]+)</a></li>!) {
			$link = $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			print "$link\t$title\n";
		}
	}
}

main();
