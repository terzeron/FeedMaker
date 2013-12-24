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
		if ($line =~ m!<li><a href="[^"]*title=([^"&]+)[^"]*"><img alt="([^"]+)"!) {
			if ($1 eq "coin") {
				# 오늘의운세는 skip
				next; 
			}
			$link = "http://sports.chosun.com/cartoon/sub_list.htm?title=" . $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			print "$link\t$title\n";
		}
	}
}

main();
