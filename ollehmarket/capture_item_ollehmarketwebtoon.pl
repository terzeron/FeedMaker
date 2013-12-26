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
	my $author = "";

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
		while ($line =~ m!
							 {
							 [^}]*,
							 "webtoonseq":(?<webtoonseq>\d+)[^}]*
							 [^}]*,
							 "webtoonnm":(?:"(?<webtoonnm>[^"]+)"|null)
							 [^}]*,
							 "authornm":(?:"(?<authornm>[^"]+)"|null)
							 [^}]*,
							 "timesseq":(?<timesseq>\d+)
							 [^}]*
							 "timestitle":(?:"(?<timestitle>[^"]+)"|null)
							 [^}]*
						 }
						 !gx) {
			if (defined $+{webtoonnm} and defined $+{authornm}) {
				# 올레마켓 웹툰목록
				$link = "http://webtoon.olleh.com/main/times_list.kt?webtoonSeq=" . $+{webtoonseq};
				$title = $+{webtoonnm} . " by " . $+{authornm};
				$title =~ s!\&\#39;!'!g;
			} else {
				# 개별 웹툰 회차
				$link = "http://webtoon.olleh.com/main/times_detail.kt?webtoonseq=" . $+{webtoonseq} . "&timesseq=" . $+{timesseq};
				$title = $+{timestitle};
				$title =~ s!\&\#39;!'!g;
			}
			print "$link\t$title\n";
			$count++;
			if ($count >= $limit_feeds) {
				last;
			}
		}
	}
}


main();
