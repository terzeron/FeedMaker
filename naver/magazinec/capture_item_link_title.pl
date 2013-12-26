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
	my $icon = "";

	while (my $line = <STDIN>) {
		if ($line =~ m!<a\s+class="[^"]+"\s+href="/(main/magazinec/index\.nhn\?componentId=\d+)"!) {
			$link = "http://news.naver.com/" . $1;
		} elsif ($line =~ m!<img.*src=\"([^\"]+)\" />!) {
			$icon = $1;
		} elsif ($line =~ m!<strong class="vol">([^<]+)</strong>!) {
			$title = $1;
		} elsif ($line =~ m!<strong class="tit">([^<]+)</strong>!) {
			print "$link\t$title $1\t$icon\n";
		}
	}
}


main();
