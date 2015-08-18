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

	while (my $line = <STDIN>) {
		while ($line =~ m!
							 [^}]*,
							 "PROD_?NM":"\s*([^"]+)\s*",
							 [^}]*,
							 "PROD_?ID":"\s*([^"]+)\s*",
						 !igx) {
			$title = $1;
			$link = "http://m.tstore.co.kr/mobilepoc/webtoon/webtoonDetail.omp?prodId=" . $2;
			print "$link\t$title\n";
		}
	}
}


main();
