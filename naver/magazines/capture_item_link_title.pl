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
		if ($line =~ m!<a href="(/magazineS/index\.nhn\?id=\d+)">([^<]+)</a>!) {
			$link = "http://sports.news.naver.com/" . $1;
			$title = $2;
			print "$link\t$title\n";
		}
	}
}


main();
