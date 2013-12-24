#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use FeedMaker;


sub get_list_page_link
{
	my $link = shift;
	my $encoding = shift;

	my $cmd = qq(wget.sh "$link" $encoding | perl -ne 'if (m!<li class="wt_ing1"><a href="(/mobilepoc/webtoon/webtoonList\\.omp\\?prodId=[^"&]+)[^"]*">[^<]*</a></li>!) { print \$1 . "\\n"; }');
	#print $cmd . "\n";
	my $result = qx($cmd);
	if ($ERRNO != 0) {
		confess "Error: can't get list page url from '$link', $ERRNO\n";
		exit(-1);
	}

	chomp $result;
	return $result;
}


sub get_config_encoding
{
	my $config = ();
	my $config_file = "conf.xml";
	if (not FeedMaker::read_config($config_file, \$config)) {
		confess "Error: can't read configuration!, ";
		return -1;
	}
	my $extraction_config = $config->{"extraction"};
	if (not defined $extraction_config) {
		confess "Error: can't read extraction config!, ";
		return -1;
	}
	my $element_list = $extraction_config->{"element_list"};
	my $element_class = $element_list->{"element_class"};
	if (not defined $element_class) {
		$element_class = "";
	}
	my $element_id = $element_list->{"element_id"};
	if (not defined $element_id) {
		$element_id = "";
	}
	my $encoding = $extraction_config->{"encoding"};
	if (not defined $encoding) {
		$encoding = "utf8";
	}

	return $encoding;
}


sub main
{
	my $link = "";
	my $title = "";
	my $state = 0;
	my @result_arr = ();

	my $encoding = get_config_encoding();

	while (my $line = <STDIN>) {
		if ($state == 0) {
			if ($line =~ m!<a[^>]*href="javascript:goStatsContentsDetail\('(/webtoon/webtoonDetail[^']+)'[^"]*"!) {
				$link = "http://m.tstore.co.kr/mobilepoc" . $1;
				$state = 1;
			} 
		} elsif ($state == 1) {
			if ($line =~ m!<(?:span|dt) class="nobr4?">?<nobr>\s*(.+)\s*</nobr></(?:span|dt)>!m) {
				$title = $1;
				#print "$link\t$title\n";
				push @result_arr, "$link\t$title";
				$state = 0;
			} elsif ($line =~ m!<div class="nobr4">!) {
				$state = 101;
			} 
		} elsif ($state == 101) {
			if ($line =~ m!^\s*<nobr>\s*(.+)\s*</nobr>\s*$!) {
				$title = $1;
				my $list_page_link = "http://m.tstore.co.kr" . get_list_page_link($link, $encoding);
				print "$list_page_link\t$title\n";
				push @result_arr, "$list_page_link\t$title";
				$state = 0;
			}
		}
	}

	my $i = 0;
	foreach my $item (@result_arr) {
		print $item . "\n";
		$i++;
		if ($i >= 5) {
			last;
		}
	}
}


main();
