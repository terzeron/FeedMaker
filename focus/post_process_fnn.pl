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

	# add the thumbnail-size icon image
	my $icon = $ARGV[1];
	if (defined $icon and $icon ne "") {
		my $icon_str = "<img src='$icon' width='250' />\n";
		print $icon_str;
	}
	
	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!(http://image.fnn.co.kr/.*\.jpg)!g) {
			my $img_url = $1;
			my $img_str = "<img src='" . $img_url . "' width='100%'/><br/>\n";
			print $img_str;
		}
	}
}	


main();
