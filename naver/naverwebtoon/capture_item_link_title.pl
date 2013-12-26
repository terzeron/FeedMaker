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
		if ($line =~ m!<a href="/(webtoon/list.nhn\?titleId=\d+)[^"]*"[^>]*><img[^>]*title="([^"]+)"[^>]*/?>!) {
			$link = $1;
			$title = $2;
			$link = "http://comic.naver.com/" . $link;
			print "$link\t$title\n";
		}
	}
}


main();
