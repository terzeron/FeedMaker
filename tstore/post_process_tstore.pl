#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker;


sub main
{
	my $img_url_prefix = "";
	my $img_index = "";
	my $img_ext = "";
	my $state = 0;

	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!<img src='(http://m.tstore.co.kr/SMILE_DATA[^']+)(\d+)\.(jpg)'/>!) {
				$img_url_prefix = $1;
				$img_index = int($2);
				$img_ext = $3;
				$state = 1;
			}
		} elsif ($state == 1) {
			# 시작 인덱스
			if ($line =~ m!^\s*1</span>\s*$!) {
				$state = 2;
			}
		} elsif ($state == 2) {
			if ($line =~ m!^\s*/<span>\s*$!) {
				$state = 3;
			}
		} elsif ($state == 3) {
			# 종료 인덱스
			if ($line =~ m!^\s*(\d+)</span>\s*$!) {
				my $img_last_index = int($1);
				for (my $i = 1; $i <= $img_last_index; $i++) {
					print "<img src='$img_url_prefix$i.$img_ext' width='100%'/>\n";
				}
				last;
			}
		}
	}
}


main();
