#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker;


sub main
{
	my $img_prefix = "";
	my $img_index = -1;

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!(http://image.fnn.co.kr/.*\.(gif|jpg|png))!g) {
			my $img_url = $1;
			my $img_str = "<img src='" . $img_url . "' width='100%'/><br/>\n";
			print $img_str;
		}
	}
}	


main();
