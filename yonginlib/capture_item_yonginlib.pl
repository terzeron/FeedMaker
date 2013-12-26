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
	my $author = "";
	my $state = 0;

	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!<a href="(http://ebook.yonginlib.go.kr/Kyobo_T3/Content/ebook/ebook_View.asp\?[^"]+)"><img alt="[^"]+" src="[^"]+"/></a>!) {
				$link = $1;
				$link =~ s!&amp;!&!g;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<a href="http://ebook.yonginlib.go.kr/Kyobo_T3/Content/ebook/ebook_View.asp\?[^"]+">(.+)</a>!) {
				$title = $1;
				$state = 2;
			}
		} elsif ($state == 2) {
			if ($line =~ m!\s*(.+)\s*/\s*\[\s*.*\s*/\s*\d+-\d+-\d+\s*\]!) {
				$author = $1;
				print "$link\t$title - $author\n";
				$state = 0;
				$link = "";
				$title = "";
				$author = "";
			}
		}
	}
}


main();
