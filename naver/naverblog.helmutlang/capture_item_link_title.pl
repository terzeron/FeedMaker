#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use URI::Encode qw(uri_decode);


sub main
{
	my $link = "";
	my $title = "";
	my $url_prefix = "http://blog.naver.com/PostView.nhn?blogId=helmut_lang&logNo=";

	while (my $line = <STDIN>) {
		while ($line =~ m!{"logNo":"(\d+)","title":"([^"]+)",!g) {
			my $logno = $1;
			$title = uri_decode($2);
			$title =~ s/\+/ /g;
			$title =~ s/&quot;/'/g;
			$link = $url_prefix . $logno;
			print "$link\t$title\n";
		}
	}
}


main();
