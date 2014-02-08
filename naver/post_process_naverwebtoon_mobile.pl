#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use Digest::MD5;
use FeedMaker qw(read_config get_md5_name);


sub main
{
	my $img_host = "";
	my $img_path = "";
	my $img_index = -1;
	my $img_ext = "jpg";
	my $img_url = "";
	my $cache_url = "";
	my $cache_file = "";
	my $page_url = $ARGV[0];

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!<(meta|style)!) {
			print $line . "\n";
		} elsif ($line =~ m!<img src='http://(imgcomic.naver.(?:com|net))/([^']+_)(\d+)\.(jpg|gif)!gi) {
			$img_host = $1;
			$img_path = $2;
			$img_index = $3;
			$img_ext = $4;
			print "<img src='http://${img_host}/${img_path}${img_index}.${img_ext}' width='100%'/>\n";
		} elsif ($line =~ m!<img src='http://(imgcomic.naver.(?:com|net))/([^']+)\.(jpg|gif)!gi) {
			$img_host = $1;
			$img_path = $2;
			$img_ext = $3;
			print "<img src='http://${img_host}/${img_path}.${img_ext}' width='100%'/>\n";
		}
		#print $line . "\n";
	}
	#print "img_path=$img_path, img_index=$img_index\n";

	if ($img_path ne "" and $img_index >= 0) {
		# add some additional images loaded dynamically
		for (my $i = int($img_index) + 1; $i < 50; $i++) {
			#my $format = "%1" . length($img_index) . "d";
			#my $img_url = $img_path . sprintf($format, $i) . "." . $img_ext;
			$img_url = "http://" . $img_host . "/" . $img_path . $i . "." . $img_ext;
			print "<img src='http://${img_host}/${img_path}${i}.${img_ext}' width='100%'/>\n";
		}
	}
}	


main();
