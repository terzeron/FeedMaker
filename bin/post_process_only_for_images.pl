#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker;


sub main
{
	while (my $line = <STDIN>) {
		if ($line =~ m!<(meta|style)!) {
			print $line;
		} elsif ($line =~ m!<img src=(['"])(http://[^'"]+)(?:['"])[^>]*/>!) {
			print $line;
		}
	}
}


main();
