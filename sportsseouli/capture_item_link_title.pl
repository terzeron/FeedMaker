#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use Getopt::Std;

use FeedMaker qw(utf8_encode);
use URI::Encode qw(uri_decode);
use Scalar::Util qw(reftype);
use JSON qw(decode_json);


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
	my $content = "";
	my @arr = ();

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

	while (my $line = <STDIN>) {
		$content .= $line;
	}
	my $data = decode_json($content);
	if (defined $data and reftype($data) eq "ARRAY") {
		my $map_ref = $data->[0];
		my $id = $map_ref->{"cm_id"};
		my $volume = $map_ref->{"cd_volume"};
		for (my $i = 1; $i <= $volume; $i++) {
			$link = "http://mobile.sportsseouli.com/cartoon/read?cm_id=$id&cm_cnt=$i";
			$title = utf8_encode(uri_decode($map_ref->{"cm_title"})) . " $i회";
			#print "$link\t$title\n";
			push @arr, "$link\t$title";
		}
	}

	my $count = 0;
	for my $item (reverse @arr) {
		if ($count >= $limit_feeds) {
			last;
		}
		print $item . "\n";
		$count++;
	}
}


main();
