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
		if ($line =~ m!^<a href="(view\.php\?id=[^"]+)"><font class="list_title">([^<]+)</font></a>!) {
			$link = "https://www.ppomppu.co.kr/zboard/" . $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			$link =~ s!&page=\d+!!g;
			$title =~ s!\s+! !g;
			if ($title =~ /^(\s|　)*$/) {
				$title = "무제";
			}
			if ($title =~ m!(유후|내방만)!) { 
				next;
			}
			print "$link\t$title\n";
		}
	}
}


main();
