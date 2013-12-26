#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;


sub main
{
	my $state = 0;
	my $link = 0;
	my $title = 0;

	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!<a class="cds_a" href="/(mobile_contents\.nhn\?contents_id=\d+)"!) {
				$link = "http://m.navercast.naver.com/" . $1;
				$state = 1;	
			}
		} elsif ($state == 1) {
			if ($line =~ m!<h3 class="cds_h3">([^<]+)</h3>!) {
				$title = $1;
				print $link . "\t" . $title . " - " . $1 . "\n";
				$state = 0;
			}
		}
	}
}


main();
