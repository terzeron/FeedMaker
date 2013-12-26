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
	my $title = "";
	my $state = 0;

	while (my $line = <STDIN>) {
		if ($state == 0) {
			# json 
			while ($line =~ m!{"PART_CNT":[^}]*,"PROD_NM":"([^"]+)",[^}]*,"PROD_ID":"(\w+)",[^}]*}!g) {
				$title = $1;
				$link = "http://m.tstore.co.kr/mobilepoc/webtoon/webtoonDetail.omp?prodId=" . $2;
				print "$link\t$title\n";
				next;
			}
			
			# html
			if ($line =~ m!<a[^>]*href="javascript:goStatsContentsDetail\('(/webtoon/webtoonDetail[^']+)'[^"]*" class="toon03">!) {
				$link = "http://m.tstore.co.kr/mobilepoc" . $1;
				$state = 1;
			} 
		} elsif ($state == 1) {
			if ($line =~ m!<(?:span|dt) class="nobr4?">?<nobr>\s*(.+)\s*</nobr></(?:span|dt)>!m) {
				$title = $1;
				print "$link\t$title\n";
				$state = 0;
			} elsif ($line =~ m!<div class="nobr4">!) {
				$state = 101;
			} 
		} elsif ($state == 101) {
			if ($line =~ m!^\s*<nobr>\s*(.+)\s*</nobr>\s*$!) {
				$title = $1;
				print "$link\t$title\n";
				$state = 0;
			}
		}
	}
}


main();
