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
	my $state = 0;

	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!<a href="(bbscontent\.aspx\?[^"]+)" id="[^"]+">!) {
				$link = "http://www.mule.co.kr/community/" . $1;
				$link =~ s!&amp;!&!g;
				$link =~ s!&page=\d+!!g;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<span id="[^"]+Label[^"]+">([^<]+)(\s*<font color="\w+">\(\d+\)</font>)?</span></a>!) {
				$title = $1;
				$title =~ s!\s+! !g;
				print "$link\t$title\n";
				$state = 0;
			}
		}
	}
}

main();
