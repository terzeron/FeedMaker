#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use FeedMaker;


sub get_title
{
	my $url = shift;
	my $encoding = shift;

	print "# get_title($url, $encoding)\n";

	my $state = 0;
	my $cmd = qq(wget.sh "$url" "$encoding");
	my $result = `$cmd`;
	if ($CHILD_ERROR != 0) {
	    confess "Error: can't get html from '$url',";
		return;
	} else {
		my $html = $result;
		my $headline = "";
		foreach my $line (split /\n/, $html) {
			if ($line =~ m!<div class="bx_top_section">!) {
				$state = 1;
			}
			if ($state == 1) {
				if ($line =~ m!<div class="bx_in_coverstory2">!) {
					$state = 2;
				}
				if ($line =~ m!<p>(.+)</p>!i) {
					my $i = 0;
					foreach my $word (split /\s+/, $1) {
						$headline .= $word . " ";
						if ($i++ > 10) {
							last;
						}
					}
					$headline .= "...";
				}
			}
			if ($line =~ m!<h5>(.*)</h5>!) {
				my $title = $1;
				$title =~ s!<br>! - !g;
				if ($title ne "" and $title !~ m!^Chapter\s*\d+!i and 
					$title !~ m!^\d+\.\s*! and $title !~ m!prologue!i) {
					return $title;
				}
			}
		}
		return $headline;
	}
}


sub main
{
	my $conf_file = $ARGV[0];
	my $config = ();

	if (not FeedMaker::read_config($conf_file, \$config)) {
		confess "Error: can't read configuration file '$conf_file'\n";
		return -1;
	}	
	my $encoding = get_config_value($config, 0, ("collection", "encoding"));
	if (not defined $encoding or $encoding eq ""){
		$encoding = "utf8";
	}

	while (my $line = <STDIN>) {
		if ($line =~ m!<a href=\"(cstory\.nhn\?nid=\d+)&(?:amp;)?page=\d+\"><img src="?[^>]+"?\s*/?></a>!) {
			my $url = $1;
			my $title = get_title("http://movie.naver.com/movie/mzine/$url", $encoding);
			if ($title eq "") {
				$title = "제목없음";
			}
			print "http://movie.naver.com/movie/mzine/$1\t$title\t\n";
		}
	}
}


main();
