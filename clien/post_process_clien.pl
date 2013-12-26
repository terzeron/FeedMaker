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
		chomp $line;
		if ($line =~ m!<(meta|style)!) {
			next;
		} elsif ($line =~ m!^(.*)<img src=\'\.\./([^\']+)\'/>(.*)$!) {
			print $1 . "<img src='https://www.voigtclub.com/" . $2 . "'/>" . $3 . "\n";
		}
	}
}	


main();
