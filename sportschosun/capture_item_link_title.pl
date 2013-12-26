#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
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
	my $episode_num = "";
	my $state = 0;

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
		if ($state == 0) {
			if ($line =~ m!<li class="section1">([^<]+)</li>!) {
				$episode_num = $1;
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ m!<li class="section2"><a href="([^"]+)">\[[^\]]+\] ([^<]+)</a></li>!) {
				$link = $1;
				$title = $2;
				$link =~ s!&amp;!&!g;
				$link = "http://sports.chosun.com/cartoon/" . $link;
				$title = $episode_num . " " . $title;
				print "$link\t$title\n";
				$count++;
				if ($count >= $limit_feeds) {
					last;
				}
				$state = 0;
			}
		}
	}
}


main();
