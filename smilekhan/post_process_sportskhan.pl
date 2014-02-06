#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker;


sub get_config
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
	my @url_list = ();

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!<a href='(http://[^']+)'[^>]*>\d+</a>!) {
			push(@url_list, $1);
		} elsif ($line =~ m!<img src='([^']+)'[^>]*>!) {
			print "<img src='" . $1 . "' width='100%'/>\n";
		}
	}

	my $encoding = get_config();

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
