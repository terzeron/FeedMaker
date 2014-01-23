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
		if ($line =~ m!<p><a href="/(webtoon/view/[^"]+)" title="([^"]+)">.+</a></p>!) {
			$link = "http://cartoon.media.daum.net/" . $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			print "$link\t$title\t$icon\n";
		}
	}
}


main();