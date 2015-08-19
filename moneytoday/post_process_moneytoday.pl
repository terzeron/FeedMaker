#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker qw(get_encoding_from_config);


sub main
{
	my $second_page_url = "";

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!<img src='(http://comicmenu.mt.co.kr/[^']+.jpg)'(?: width='\d+%')?/>!i) {
			my $img_url = $1;
			# 광고 이미지 skip
			if ($img_url =~ m!http://comicmenu\.mt\.co\.kr/list/\d+_list_original_page1_5_a7e77\.jpg!i) {
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
		my $encoding = get_encoding_from_config();

        my $cmd = qq(wget.sh "$second_page_url" | extract.py "$ARGV[0]");
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
