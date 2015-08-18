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

	# idempotent 
	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!<a class="title_cr" href="(?<link>http://article.joins.com/news/article/[^"]+)!) {
				$link = $+{"link"};
				$link =~ s/\&amp;/&/g;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!^\s+(?<title>\S.*\S)\s*$!) {
				$title = $+{"title"};
				print "$link\t$title\n";
				$state = 2;
			}
		} elsif ($state == 2) {
			if ($line =~ m!</a>!) {
				$state = 0;
			}
		}
	}
}

main();
