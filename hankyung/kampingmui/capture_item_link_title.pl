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
	my $chapter = 0;

	while (my $line = <STDIN>) {
		if ($line =~ m!<h3>제(\d+)장 [^<]*</h3>!) {
			$chapter = $1;
		} elsif ($line =~ m!<option value="(\d+)"!) {
			my $num = $1;
			$link = "http://w.hankyung.com/board/view.php?id=community_kbm&category=" .  $chapter . "&page=&no=" . $num;
			$title = "금병매 $chapter장 $num회";
			print "$link\t$title\n";
		}
	}

}

main();
