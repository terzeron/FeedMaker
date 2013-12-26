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
	my $state = 0;

	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!<a class="card" href="/?(contents\.nhn\?contents_id=\d+)[^"]*"[^>]*>!) {
				$link = $1;
				$link =~ s!&amp;!&!g;
				$link = "http://navercast.naver.com/" . $link;
				$state = 1;
			}
		} elsif ($state == 1) {
			#<strong>긍정·낙관·확신하면 꿈꾼 대로 이루어지는가?</strong><span></span>
			#<strong>최석정</strong><span>현실 가능한 정책을 제시한 소론 정치가</span>
			if ($line =~ m!<strong>([^<]+)</strong><span(?: alt="[^"]+" title="([^"]+)")?>(.*)</span>!) {
				if (defined $2 and $2 ne "") {
					$title = $1 . " - " . $2;
				} else {
					$title = $1 . " - " . $3;
				}
				print "$link\t$title\n";
				$state = 0;
				$link = "";
				$title = "";
			}
		}
	}
}


main();
