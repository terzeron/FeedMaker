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
		if ($line =~ m!<a href="(?<link>[^"]+)"><strong class="tit">(?<title>.+)</strong></a>!) {
			$link = "http://ilyo.co.kr" . $+{"link"};
			$title = $+{"title"};
			$link =~ s!&amp;!&!g;
			print "$link\t$title\n";
		}
	}
}

main();
