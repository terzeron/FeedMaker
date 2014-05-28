#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker;


sub main
{
	my $url = "";

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!<img src='[^']*(/data/file/series/[^']*\.jpg)'!) {
			$url = $1;
			if ($url =~ m!http://!) {
				print "<img src='" . $1 . "' width='100%'/>\n";
			} else {
				print "<img src='http://am7.munhwa.com" . $1 . "' width='100%'/>\n";
			}
		}
	}
}	


main();
