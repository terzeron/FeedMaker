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
	my $url_prefix = "http://blog.naver.com/PostView.nhn?blogId=";

	while (my $line = <STDIN>) {
		if ($line =~ m!"blogId":"([^"]+)"!) {
			$url_prefix = $url_prefix . $1 . "&logNo=";
		}
		while ($line =~ m!{"logNo":"(\d+)","title":"([^"]+)",!g) {
			my $logno = $1;
			$title = uri_decode($2);
			$title =~ s/\+/ /g;
			$title =~ s/&quot;/'/g;
			$title =~ s/&(lt|gt);//g;
			$link = $url_prefix . $logno;
			print "$link\t$title\n";
		}
	}
}


main();