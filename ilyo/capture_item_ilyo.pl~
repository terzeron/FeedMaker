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
		if ($line =~ m!<a class="img" href="(?<link>[^"]+cate_id=[^"]+)">!) {
			$link = $+{"link"};
			$link =~ s!&amp;!&!g;
			$link = "http://ilyo.co.kr" . $link;
		} elsif ($line =~ m!<a href="(?:[^"]+)"><strong class="tit">(?<title>.+)</strong></a>!) {
			$title = $+{"title"};
			$title =~ s! - (.*)$!!;
			print "$link\t$title\n";
		}
	}
}

main();
