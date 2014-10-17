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
	my @result = ();

	while (my $line = <STDIN>) {
		if ($line =~ m!<a\s+class="[^"]+"\s+href="(today\.nhn[^"]+)"[^>]*>([^<]+)</a>!) {
			$link = $1;
			$title = $2;
			$link =~ s/&amp;/&/g;
			push @result, "http://today.movie.naver.com/$link\t$title";
		}
	}
	
	my $len = scalar @result;
	if ($len >= 10) {
		for (my $i = $len - 10; $i < $len; $i++) {
			print $result[$i] . "\n";	
		}
	} else {
		for (my $i = 0; $i < $len; $i++) {
			print $result[$i] . "\n";
		}
	}
}


main();
