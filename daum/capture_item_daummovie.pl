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
		if ($line =~ m!<h5><a\s+class="[^"]+"\s+href="(movieInfoArticleRead\.do[^"]+)"[^>]*>(.+)</a></h5>!) {
			$link = "http://movie.daum.net/movieinfo/news/" . $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			print "$link\t$title\n";
		}
	}
}


main();
