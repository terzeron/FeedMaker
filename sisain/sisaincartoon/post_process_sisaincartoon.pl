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
		while ($line =~ m!(http://www.sisainlive.com/.*\.jpg)!g) {
			print "<img src='" . $1 . "' width='100%'/><br/>\n";
		}
		#print $line . "\n";
	}
}	


main();
