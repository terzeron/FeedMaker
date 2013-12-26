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
			if ($line =~ m!<a href="([^"]+)">!) {
				$link = $1;
				$link =~ s!&amp;!&!g;
				$link =~ s!&week(day)?=\w\w\w!!g;
				$state = 1;
			} elsif ($line =~ m!^\s+(\S+)\s+</p>$!) {
				$title = $1;
				print "$link\t$title\n";
				$state = 0;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<img alt="([^"]+)"!) {
				$title = $1;
				print "$link\t$title\n";
				$state = 0;
			} elsif ($line =~ m!<div class="[^"]+" onclick="\w+\(\s*this\s*,\s*'([^']+)'\s*\);">!) {
				$link = $1;
				$link =~ s!&amp;!&!g;
				$link =~ s!&week(day)?=\w\w\w!!g;
				$state = 1;
			}
		}
	}
}


main();
