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
		if ($state == 0) {
			if ($line =~ m!amina_thumb\('(http://www.voigtclub.com/bbs/board.php\?bo_table=freegallery_0[^']+)'[^>]*title="([^"]+)"!) {
				$link = $1;
				$title = $2;
				$link =~ s!&amp;!&!g;
				$link =~ s!&page=\d+!!g;
				$title =~ s!\s+! !g;
				if ($title =~ /^(\s|　)*$/) {
					$title = "무제";
				}
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<div class="la-details"><span class="la-data-first la-data-name">([^<]+)</span><span class="la-data la-data-good"><span>추천 </span>(\d+)</span></div></div>!) {
				my $name = $1;
				my $num_recommend = $2;
				if (int($num_recommend) > 10) {
					$title .= " by $name";
					print "$link\t$title\n";
				}
				$state = 0;
			}
		}
	}
}


main();
