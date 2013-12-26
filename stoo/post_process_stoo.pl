#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker;


sub main
{
	my $second_page_url = "";

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!<a href='(http://[^']+)'[^>]*><img src='http://cwstatic\.asiae\.co\.kr/images/cartoon/btn_s\.gif'/>!) {
			$second_page_url = $1;
		} elsif ($line =~ m!<img src='(http://cwcontent[^']+)'.*/>!) {
			print "<img src='" . $1 . "' width='100%'/>\n";
		}
	}

	if ($second_page_url ne "") {
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

		my $cmd = qq(wget.sh "$second_page_url" $encoding | extract_element.py conf.xml extraction);
		#print $cmd . "\n";
		my $result = `$cmd`;
		if ($CHILD_ERROR == 0) {
			for my $line (split /\n/, $result) {
				if ($line =~ m!<img\s*[^>]*src=(?:'|")(http://cwcontent[^'"]+)(?:'|").*/>!) {
					print "<img src='" . $1 . "' width='100%'/>\n";
				}
			}
		}
	}
}


main();
