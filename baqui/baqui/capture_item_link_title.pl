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
		if ($line =~ m!<span\s+class="title"\s+onclick="content_view\((\d+)\)[^>]*"><span style=".+">(.*)</span>(?:&nbsp;)*(.*)</span>!) {
			$link = "http://baqui.co.kr/" . $1;
			if (defined $2 and $2 ne "") {
				$title = $2 . " - " . $3;
			} else {
				$title = $3;
			}
			$title =~ s!&#39;!'!g;
			print "$link\t$title\n";
		}
	}
}


main();
