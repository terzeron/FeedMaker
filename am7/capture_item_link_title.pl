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
		if ($line =~ m!<td[^>]*><a href="(/bbs/board.php\?bo_table=series&amp;wr_id=(\d+))[^"]*"><img[^>]*></a></td>!) {
			$link = "http://am7.munhwa.com" . $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			print "$link\t$title\n";
		}	
	}		

=pod
	my $count = 0;
	for my $item (reverse @arr) {
		if ($count >= $limit_feeds) {
			last;
		}
		print $item . "\n";
		$count++;
	}
=cut
}


main();
