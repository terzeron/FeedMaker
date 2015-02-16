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
						  <(?:dt|dd)>
						  <a
						  \s*
						  href="(/NWS_Web/View/at_pg.aspx\?CNTN_CD=\w+)">
						  (
						  [^<]+
						  \b
						  (?:\d+|첫|마지막|[① -⑮] ])       # must include an issue number
						  \b
						  [^<]+
						  )
						  </a>
					  !x) {
			$link = $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			$link = "http://www.ohmynews.com" . $link;
			print "$link\t$title\n";
		}
	}
}


main();
