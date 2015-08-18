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
	my $id = "";

	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!<a class="p_info" data-productid="(\d+)"!) {
				$id = $1;
				$link = "http://page.kakao.com/viewer?productId=" . $id;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<strong class="p_title ellipsis">([^<]+)</strong>!) {
				$title = $1;
				print "$link\t$title\n";
				$state = 0;
			}
		}
	}
}


main();
