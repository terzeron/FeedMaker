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
		if ($line =~ m!<img src='(http://sports.chosun.com[^']+)'!) {
			print "<img src='" . $1 . "' width='100%'/>\n";
		}
	}
}	


main();
