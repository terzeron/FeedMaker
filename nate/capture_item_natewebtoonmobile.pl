#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use FeedMaker;


sub main
{
	my $link = "";
	my $episode_num = "";
	my $title = "";
	my $state = 0;

	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!<a href="(/webtoon/detail\.php\?[^"]+)&amp;category=\d+">!) {
				$state = 1;
				$link = "http://comics.nate.com" . $1;
				$link =~ s!&amp;!&!g;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<span class="tel_episode">(.+)</span>!) {
				$episode_num = $1;
				$state = 2;
			}
		} elsif ($state == 2) {
			if ($line =~ m!<span class="tel_title">(.+)</span>!) {
				$title = $episode_num . " " . $1;
				print "$link\t$title\n";
				$state = 0;
			}
		}
	}
}


main();
