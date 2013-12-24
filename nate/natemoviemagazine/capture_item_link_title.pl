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
		if ($line =~ m!<dt class="[^"]+"><a href="(/mag/article/magview\?id=\d+&(?:amp;)?category=[^&"]+)">(.+)</a></dt>!) {
			$link = "http://movie.nate.com" . $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			$title =~ s!&lt;!<!g;
			$title =~ s!&gt;!>!g;
			print "$link\t$title\t$icon\n";
		}
	}
}


main();
