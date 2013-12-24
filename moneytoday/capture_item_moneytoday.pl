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
	my $icon = "";

	while (my $line = <STDIN>) {
		if ($line =~ m!<li><a\s+href="\./(comicView\.htm[^"]+)"><img\s+height="\d+"\s+src="[^"]+"[^>]*\s+width="\d+"\s*/></a><p class="[^"]+">([^<]+)<br/?><b>([^<]+)</b>(?:</br>)?</p></li>!) {
			$link = "http://comic.mt.co.kr/" . $1;
			$title = $2 . " " . $3;
			$link =~ s!&amp;!&!g;
			print "$link\t$title\t$icon\n";
		}
	}
}


main();
