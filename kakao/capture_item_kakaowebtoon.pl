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
			if ($line =~ m!<span class="title ellipsis_hd">([^<]+)</span>!) {
				$title = $1;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<input class="productId" type="hidden" value="(\d+)"!) {
				$id = $1;
				$link = "http://page.kakao.com/viewer?productId=" . $id;
				print "$link\t$title\n";
				$state = 0;
			}
		}
	}
}


main();
