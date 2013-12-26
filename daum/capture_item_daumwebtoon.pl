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
	my $price = "";
	my %hash = ();

	while (my $line = <STDIN>) {
		if ($line =~ m!data1.push\({img\s*:\s*"http://[^"]*",\s*title\s*:\s*"([^"]*)",\s*shortTitle\s*:\s*"[^"]*",\s*url\s*:\s*"/(webtoon/viewer/\d+)",.*price\s*:\s*"(\d+)"!) {
			$title = $1;
 		    $link = $2;
			$price = int($3);
			if ($price > 0) {
				next;
			}
			$link =~ s!&amp;!&!g;
			$link =~ s!&week(day)?=\w\w\w!!g;
			$link = "http://cartoon.media.daum.net/" . $link;
			if (not exists $hash{$link}) {
				$hash{$link} = 1;
				print "$link\t$title\n";
			}
		}
	}
}


main();
