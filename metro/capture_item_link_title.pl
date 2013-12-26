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
		if ($line =~ m!<a href="/news/articleView\.html\?idxno=(\d+)[^"]*sc_sub_section_code=([^&]+)[^"]*">(보르코[^<]+<\d+>)</div></a>!) {
			$link = "http://www.metroseoul.co.kr/news/articleView.html?idxno=$1&sc_sub_section_code=$2";
			$title = $3;
			$link =~ s!&amp;!&!g;
			print "$link\t$title\n";
		}
	}
}


main();
