#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use FeedMaker;


sub main
{
	my $link = "";
	my $title = "";
	my $author = "";

	while (my $line = <STDIN>) {
		while ($line =~ m!{[^}]+,"webtoonseq":(\d+),"webtoonnm":"([^"]+)",[^}]+,"authornm":"([^"]+)",[^}]+}!g) {
			$link = "http://webtoon.olleh.com/main/times_list.kt?webtoonSeq=" . $1;
			$title = $2;
			$title .= " by " . $3;
			$title =~ s!\&\#39;!'!g;
			print "$link\t$title\n";
		}
	}
}


main();
