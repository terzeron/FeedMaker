#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker qw(get_encoding_from_config);


sub main
{
	my @url_list = ();

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!<a href='(http://[^']+)'[^>]*>\d+</a>!) {
			push(@url_list, $1);
		} elsif ($line =~ m!<img src='([^']+)'[^>]*>!) {
			print "<img src='" . $1 . "' width='100%'/>\n";
		}
	}

	my $encoding = get_encoding_from_config("conf.xml");

	foreach my $url (@url_list) {
		my $cmd = qq(wget.sh "$url" $encoding);
		#print $cmd . "\n";
		my $result = `$cmd`;
		if ($CHILD_ERROR == 0) {
			for my $line (split /\n/, $result) {
				if ($line =~ m!<img\s*[^>]*src=(?:'|")?(http://images.sportskhan.net/article/[^'"\s]+)(?:'|")?[^>]*>!) {
					print "<img src='" . $1 . "' width='100%'/>\n";
				}
			}
		}
	}
}


main();
