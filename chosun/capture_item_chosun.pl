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
		if ($line =~ m!
						  (?:<span\s+class=(?:art_tit14|listTitle)>)?
						  <a\s+href=/web/\d+/(http://www.chosun.com/culture/news/\d+/\d+.html)>
						  (?:<span\s+class=(?:art_tit14|listTitle)>)?
						  (.*정이현.*연재소설.*달콤한[^<]*)
						  (?:</a>)?
						  (?:</span>)?
					  !x) {
			$link = $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			print "$link\t$title\n";
		}
	}
}


main();
