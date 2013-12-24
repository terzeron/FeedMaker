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
							 "PROD_NM":"\s*([^"]+)\s*",
							 [^}]*,
							 "PROD_ID":"\s*([^"]+)\s*",
						 !gx) {
			$title = $1;
			$link = "http://m.tstore.co.kr/mobilepoc/webtoon/webtoonDetail.omp?prodId=" . $2;
			print "$link\t$title\n";
		}
	}
}


main();
