#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use FeedMaker qw(get_date_str get_list_file_name);


sub get_title_year
{
	my $title = shift;
	$title =~ tr/\.|\,|\(|\)/ /d;
	#print $title . "\n";
	if ($title =~ m!^([가-핳\d\-\ \?\:]+)\s*([A-Za-z0-9\-\ \?\:]+)\s*(19\d\d|20\d\d)!) {
		#print "1  $1 --- $2 --- $3";
		return "$1\t$2\t$3";
	} elsif ($title =~ m!^([가-핳\d\-\ \?\:]+)\s*([A-Za-z0-9\-\ \?\:]+)\s*!) {
		#print "2  $1 --- $2 --- ";
		return "$1\t$2\t";
	} elsif ($title =~ m!^([가-핳\d\-\ \?\:]+)\s*(19\d\d|20\d\d)!) {
		#print "3  $1 ---  --- $2";
		return "$1\t\t$2";
	} elsif ($title =~ m!^([A-Za-z0-9\-\ \?\:]+)\s*(19\d\d|20\d\d)!) {
		#print "4   --- $1 --- $2";
		return "\t$1\t$2";
	}
	return "\t\t";
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
			if ($title !~ m!201[234]!) {
				next;
			}

			my $review_point;
			if (exists $link_point_map{$link} and defined $link_point_map{$link} and $link_point_map{$link} ne "") {
				$review_point = $link_point_map{$link};
			} else {
				my $params = get_title_year($title);
				my ($korean_title, $english_title, $year) = split /\t/, $params;	
				my $keyword = "";
				#print "### $params\n";
				if (defined $english_title and $english_title ne "") {
					$keyword = $english_title;
				} elsif (defined $korean_title and $korean_title ne "") {
					$keyword = $korean_title;
				}
					
				chomp $keyword;
				if ($keyword ne "") {
					my $cmd = qq(get_review_point.py "movie" "$keyword" "$year");
					#print "$cmd\n";
					my $result = qx($cmd);
					if ($CHILD_ERROR == 0) {
						chomp $result;
						$review_point = $result;
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
