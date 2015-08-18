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

	while (my $line = <STDIN>) {
		if ($line =~ m!<img src='(http://m.tstore.co.kr/SMILE_DATA[^']+\/)(\d+)\.(jpg)'[^>]*/>!) {
			$img_url_prefix = $1;
			$img_index = int($2);
			$img_ext = $3;
		}
	}

	for (my $i = $img_index; $i <= 20; $i++) {
		my $url = "$img_url_prefix$i.$img_ext";
		print "<img src='$url' width='100%'/>\n";
	}
}


main();
