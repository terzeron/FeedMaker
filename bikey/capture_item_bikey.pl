#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;


sub main
{
	my $link = "";
	my $title = "";

	while (my $line = <STDIN>) {
		if ($line =~ m!<a\s+class="subjectColor"\s+href="(board\.php[^"]+)"[^>]*>!) {
 		    $link = $1;
			$link =~ s!&amp;!&!gi;
 		    $link = "http://www.bikey.co.kr/new/" . $link;
		} elsif ($line =~ m!<span style="[^"]+">([^<]+)</span>!) {
			$title = $1;
			print "$link\t$title\n";
		}
	}
}


main();
