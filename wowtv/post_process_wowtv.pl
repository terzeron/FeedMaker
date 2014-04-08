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
	my $img_postfix = "";
	my $img_index = 0;
	my $img_index_len = 0;
	my $img_ext = "";
	my $delimiter = "";
	my $page_url = $ARGV[0];

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!<(meta|style)!) {
			print $line;
		} elsif ($line =~ m!^(\d+)페이지</span>!) {
			if (int($1) > $max_num_pages) {
				$max_num_pages = int($1);
			}
		} elsif ($line =~ m!<img src='(?<url>(?<prefix>http://[^\\]+)\\(?<index>\d+)\.(?<ext>jpg|png|gif))'/>!) {
			my $url = $+{"url"};
			$img_prefix = $+{"prefix"};
			$img_index = $+{"index"};
			$img_index_len = length($img_index);
			$img_ext = $+{"ext"};
			$delimiter = "\\";
			print "<!-- $img_prefix $img_index $img_ext -->\n";
			print "<img src='$url' width='100%'/>\n";
		} elsif ($line =~ m!<img src='(?<url>(?<prefix>http://.+)_(?<postfix>\w+)(?<index>\d+)\(\d+\)\.(?<ext>jpg|png|gif))'/>!) {
			my $url = $+{"url"};
			$img_prefix = $+{"prefix"};
			$img_postfix = $+{"postfix"};
			$img_index = $+{"index"};
			$img_index_len = length($img_index);
			$img_ext = $+{"ext"};
			$delimiter = "_";
			print "<!-- $img_prefix $img_index $img_ext -->\n";
			print "<img src='$url' width='100%'/>\n";
		} elsif ($line =~ m!<img src='(?<url>(?<prefix>http://.+)_(?<postfix>\w+)(?<index>\d+)\.(?<ext>jpg|png|gif))'/>!) {
			my $url = $+{"url"};
			$img_prefix = $+{"prefix"};
			$img_postfix = $+{"postfix"};
			$img_index = $+{"index"};
			$img_index_len = length($img_index);
			$img_ext = $+{"ext"};
			$delimiter = "_";
			print "<!-- $img_prefix $img_index $img_ext -->\n";
			print "<img src='$url' width='100%'/>\n";
		}
	}

	if ($max_num_pages > 0 and $img_prefix ne "" and $delimiter ne "") {
		for (my $i = $img_index + 1; $i <= $max_num_pages * 2; $i++) {
			if ($delimiter eq "\\") {
				printf("<img src='%s/%0" . $img_index_len . "d.%s' width='100%%'>\n", $img_prefix, $i, $img_ext);
			} elsif ($delimiter eq "_") {
				printf("<img src='%s_%s%0" . $img_index_len . "d.%s' width='100%%'>\n", $img_prefix, $img_postfix, $i, $img_ext);
			}
		}
	}
}       


main();
