#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker;


sub main
{
	my $max_num_pages = 0;
	my $img_prefix = "";
	my $img_index = 0;
	my $img_index_len = 0;
	my $img_ext = "";

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!<(meta|style)!) {
			print $line;
		} elsif ($line =~ m!^(\d+)페이지</span>!) {
			if (int($1) > $max_num_pages) {
				$max_num_pages = int($1);
			}
		} elsif ($line =~ m!<img src='(http://[^\\]+)\\(\d+)\.(jpg|png|gif)'/>!) {
			$img_prefix = $1;
			$img_index = $2;
			$img_index_len = length($img_index);
			$img_ext = $3;
			#print "$img_prefix $img_index $img_ext\n";
			last;
		}
	}

	for (my $i = 1; $i <= $max_num_pages * 2; $i++) {
		printf("<img src='%s/%0" . $img_index_len . "d.%s' width='100%%'>\n", $img_prefix, $i, $img_ext);
	}
}       


main();
