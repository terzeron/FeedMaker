#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use FeedMaker qw(get_date_str get_list_file_name);


sub get_title
{
	my $title = shift;
	my $arg = shift;

	$title =~ s/\\'/'/g;
	$title =~ s/(\(|\/)?(무)?설치(판|본)?\)?//g;
	$title =~ s/(steam edition|DRM free|collector's edition|ultimate edition|gegendary edition|patch|dlc)//gi;
	$title =~ s/(REPACK|TiNYiSO|PROPHET|HOG|ViTALiTY|LinGon|SKIDROW|GOG|PROPHET|RELOADED)//g;
	my $english_title = "";
	foreach my $word (split /(\s|\(|\)|,|:)+/, $title) {
		if ($word =~ m!^[\w\d]+$!) {
			$english_title .= " " . $word;
		}
	}
		
	$english_title =~ s/(^\s+|\s+$)//;
	return $english_title;
}


sub main
{
	my $link = "";
	my $title = "";
	my %link_point_map = ();

	my $ts = time();
	my $SECONDS_PER_DAY = 60 * 60 * 24;
	for (my $i = 0; $i <= 7; $i++) {
		my $date_str = get_date_str($ts - $i * $SECONDS_PER_DAY);
		my $filename = get_list_file_name("newlist", $date_str);
		if (not open(IN, $filename)) {
			next;
		}
		while (my $line = <IN>) {
			chomp $line;
			my ($link, $title, $review_point) = split /\t/, $line;
			if (defined $review_point) {
				$link_point_map{$link} = $review_point;	
			}
		}
		close(IN);
	}

	while (my $line = <STDIN>) {
		if ($line =~ m!<a href="\.\./(bbs/board.php\?bo_table=[^"]+&amp;wr_id=\d+[^\"]*)"><span>(?:\[[^\]]*\]\s*)*(.*)</span></a>!) {
			$link = "http://www.torrentrg.com/" . $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			$link =~ s!&page=\d+!!g;
			$title =~ s!\s+! !g;

			my $review_point;
			if (exists $link_point_map{$link} and defined $link_point_map{$link} and $link_point_map{$link} ne "") {
				$review_point = $link_point_map{$link};
			} else {
				my $english_title = get_title($title);
				my $keyword = "";
				#print "### $title: $params\n";
				if (defined $english_title and $english_title ne "") {
					$keyword = $english_title;
					if ($keyword ne "") {
						my $cmd = qq(get_review_point.py "game" "$keyword");
						print "# $cmd\n";
						my $result = qx($cmd);
						if ($CHILD_ERROR == 0) {
							chomp $result;
							$review_point = $result;
						}
					}
				}
				if (not defined $review_point or $review_point eq "") {
					$review_point = "0.0";
				}
			}
			
			print "$link\t$title\t$review_point\n";
		}
	}
}


main();
