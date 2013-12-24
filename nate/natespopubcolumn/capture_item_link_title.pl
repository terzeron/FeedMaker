#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;

use FeedMaker;


sub process_a_page
{
	my $data = shift;

	my $link = "";
	my $title = "";
	my $icon = "";
	my $count = 0;
	my @lines = split /\n|\r/, $data;

	foreach my $line (@lines) {
		if ($line =~ m!<dt><a href="(http://sports.news.nate.com/view/[^"]+)"><strong>(.+)</strong></a></dt>!) {
			$link = $1;
			$title = $2;
			$title =~ s!&\#124;!|!g;
			print "$link\t$title\t$icon\n";
			last;
		}
	}
}

sub main
{
	my $url = "";

	my $config_file = "conf.xml";
	my $config = ();
	if (not FeedMaker::read_config($config_file, \$config)) {
		confess "Error: can't read configuration!, ";
		return -1;
	}
	my $extraction_config = $config->{"extraction"};
	if (not defined $extraction_config) {
		confess "Error: can't read extraction config!, ";
		return -1;
	}

	my $encoding = $extraction_config->{"encoding"};
	if (not defined $encoding) {
		$encoding = "utf8";
	}

	while (my $line = <STDIN>) {
		if ($line =~ m!<dt><a href="(http://sports.news.nate.com/spopub/column\?cp=(\w+))">(.+)</a></dt>!) {
			$url = $1;
			$url =~ s!&amp;!&!g;
			$url =~ s!</?em>!!g;
			my $cmd = qq(wget.sh "$url" $encoding);
			#print "$cmd\n";
			my $result = `$cmd`;
			if ($CHILD_ERROR != 0) {
				confess "Error: can't execute '$cmd', $ERRNO\n";
				return;
			}
			#print $result;
			process_a_page($result);
		}
	}
}


main();
