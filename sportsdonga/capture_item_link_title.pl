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
	my $url_prefix = "";
	my $state = 0;
	my @result_arr = ();

	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!window\.location\.href\s*=\s*"([^"]+)"!) {
				$url_prefix = "http://sports.donga.com/cartoon" . $1;
				$state = 1;
			}
		} elsif ($state == 1) {
			while ($line =~ m!<option (?:selected="" )?value="(\d+)">([^<]+)</option>!g) {
				$title = $2;
				$link = $url_prefix . $1;
				push @result_arr, "$link\t$title";
			}
		}
	}

	for (my $i = 0; $i < 10; $i++) {
		my $result = pop @result_arr;
		print $result . "\n";
	}
}


main();
