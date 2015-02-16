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

	# <dt><a href="/NWS_Web/View/at_pg.aspx?CNTN_CD=A0000350156">추리무협소설 &lt;천지&gt; 2회</a></dt>
	while (my $line = <STDIN>) {
		if ($line =~ m!<dt><a href="(/NWS_Web/View/at_pg.aspx\?CNTN_CD=\w+)">추리무협소설 &lt;천지&gt; (\d+회)</a></dt>!) {
			$link = $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			$link = "http://www.ohmynews.com" . $link;
			print "$link\t$title\n";
		}
	}
}


main();
