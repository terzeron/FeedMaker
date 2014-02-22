#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;


sub main
{
	my $img_prefix = "";
	my $img_index = -1;
	my $img_ext = "jpg";
	my $img_url = "";
	my $cache_url = "";
	my $cache_file = "";
	my $page_url = $ARGV[0];
	my $num_units = 5;

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!<(meta|style)!) {
			print $line . "\n";
		} elsif ($line =~ m!<img src='(http://webtoon\.olleh\.com/download/webtoon/[^']+)\.(jpg|gif|png)'!gi) {
			$img_prefix = $1;
			$img_ext = $2;
			$img_url = $img_prefix . "." . $img_ext;
			print "<img src='$img_url' width='100%'/>\n";
		}
	}
}	


main();
