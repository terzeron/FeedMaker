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
		if ($line =~ m!<img src='(http://comicmenu.mt.co.kr/[^']+.jpg)'(?: width='\d+%')?/>!i) {
			my $img_url = $1;
			# 광고 이미지 skip
			if ($img_url =~ m!http://comicmenu.mt.co.kr/list/\d+_list_original_page1_2_[^\.]+.jpg!i or $img_url =~ m!http://comicmenu.mt.co.kr/banner/comic_\d+_100811.jpg!i) {
				next;
			}
			print "<img src='" . $img_url . "' width='100%'/>\n";
		} elsif ($line =~ m!<(style|meta)!) {
			print $line . "\n";
		}

		if ($line =~ m!<a href='(http://[^']+)'[^>]*>!) {
			$second_page_url = $1;
		} elsif ($line =~ m!<img src='http://comicmenu\.mt\.co\.kr/images/btn_cartoon_2p\.gif'/>!) {
			last;
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

        my $cmd = qq(wget.sh "$second_page_url" $encoding | extract.py conf.xml "$ARGV[0]");
        my $result = qx($cmd);
        foreach my $line (split /\n/, $result) {
			if ($line =~ m!<img src='(http://comicmenu.mt.co.kr/[^']+.jpg)'(?: width='\d+%')?/>!i) {
				my $img_url = $1;
				if ($img_url =~ m!http://comicmenu.mt.co.kr/list/\d+_list_original_page1_2_[^\.]+.jpg!i or $img_url =~ m!http://comicmenu.mt.co.kr/banner/comic_\d+_100811.jpg!i) {
					next;
				}
				print "<img src='" . $img_url . "' width='100%'/>\n";
			}
        }
	}
	
	my $icon = $ARGV[1];
	if (defined $icon and $icon ne "") {
		print "<img src='$icon' />\n";
	}
}


main();
