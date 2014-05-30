#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;


sub main
{
	my $state = 0;
	my $link = 0;
	my $title = 0;

	while (my $line = <STDIN>) {
		if ($line =~ m!<a class="cds_send[^>]*data-title="([^"]+)"[^>]*data-url="[^"]*contents_id=(\d+)!) {
			$title = $1;
			$link = "http://m.navercast.naver.com/mobile_contents.nhn?contents_id=" . $2;
			print $link . "\t" . $title . "\n";
		}
	}
}


main();
