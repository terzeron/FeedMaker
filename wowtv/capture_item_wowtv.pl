#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use FeedMaker;
use Getopt::Std;


sub print_usage
{
	print "usage:\t$PROGRAM_NAME [ -n <limit of recent feeds> ] conf.xml\n";
	print "\n";
	exit(-1);
}


sub main
{
	my $link = "";
	my $title = "";

	my %opts = ();
	my $opt_str = "n:";
	my $limit_feeds = 10000;
	our $opt_n;
	getopts($opt_str, \%opts);
	if (defined $opts{"n"}) {
		if ($opts{"n"} =~ m!^\s*\d+\s*$!) {
			$limit_feeds = $opts{"n"};
		} else {
			print_usage();
		}
	}

	my $count = 0;
	while (my $line = <STDIN>) {
		if ($line =~ m!<option[^>]*value="(\d+)"[^>]*>(.*)</option>!) {
			$link = "http://www.wowtv.co.kr/funfun/fun/webtoon/view.asp?webtoonIdx=" . $1;
			$title = $2;
			print "$link\t$title\n";
			$count++;
			if ($count >= $limit_feeds) {
				last;
			}
		}
	}
}


main();
