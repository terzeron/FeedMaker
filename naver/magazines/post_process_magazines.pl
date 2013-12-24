#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker;


sub main
{
	my $state = 0;
	while (my $line = <STDIN>) {
		chomp $line;
		#print "####### $state #######\n";
		if ($state == 0) {
			if ($line =~ s!<img src=\"http://imgnews.naver.(com|net)/image/sports/\d+/magazineS/magazine_content/magazineS_\d+/\d+_file_image_0.jpg\" width=\"67\" height=\"9\" alt=\"[^\"]+\" />!PEOPLE!) {
				$state = 1;
			}
		} elsif ($state == 1) {
			if ($line =~ s!<img src=\"http://imgnews.naver.(com|net)/image/sports/\d+/magazineS/magazine_content/magazineS_\d+/\d+_file_image_0.jpg\" width=\"102\" height=\"10\" alt=\"[^\"]+\" />!SPECIAL REPORT!) {
				$state = 2;
			}
		} elsif ($state == 2) {
			if ($line =~ s!<img src=\"http://imgnews.naver.(com|net)/image/sports/\d+/magazineS/magazine_content/magazineS_\d+/\d+_file_image_0.jpg\" width=\"57\" height=\"10\" alt=\"[^\"]+\" />!COLUMN!) {
				$state = 3;
			}
		} elsif ($state == 3) {
			if ($line =~ s!<h2><img src=\"http://imgnews.naver.(com|net)/image/sports/\d+/magazineS/magazine_content/magazineS_\d+/\d+_file_image_0.jpg\" width=\"58\" height=\"10\" alt=\"[^\"]+\" /></h2>.*!!) {
				$state = 4;
			}
		} elsif ($state == 4) {
			if ($line =~ s!<img src=\"http://imgnews.naver.(com|net)/image/sports/\d+/magazineS/magazine_content/magazineS_\d+/\d+_file_image_0.jpg\" width=\"29\" height=\"10\" alt=\"[^\"]+\" />!POLL!) {
				$state = 5;
			} else {
				next;
			}
		} elsif ($state == 5) {
			if ($line =~ s!^<div><ul>!<h2>ZOOM IN</h2><ul>!) {
				$state = 6;
			}
		} elsif ($state == 6) {
			if ($line =~ s!^</li></ul></div>$!</li></ul>!) {
				last;
			}
		}
		print $line . "\n";
	}
	
	my $icon = $ARGV[1];
	if (defined $icon and $icon ne "") {
		print "<img src='$icon' />\n";
	}
}


main();
