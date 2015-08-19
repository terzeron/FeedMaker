#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use Digest::MD5;
use FeedMaker qw(read_config get_encoding_from_config);


sub main
{
	my $img_prefix = "";
	my $img_index = -1;
	my $img_ext = "jpg";
	my $num_units = 25;

	while (my $line = <STDIN>) {
		print $line;
	}

	my $encoding = get_encoding_from_config();

	my $post_link = $ARGV[0];
	if ($post_link =~ m!http://cartoon\.media\.daum\.net/(m/)?webtoon/viewer/(\d+)$!) {
		my $mobile = $1;
		my $episode_id = $2;
		my $cmd = "";
		my $url = "";
		if (defined $mobile and $mobile eq "m/") {
			$url = "http://cartoon.media.daum.net/data/mobile/webtoon/viewer?id=$episode_id";
		} else {
			$url = "http://cartoon.media.daum.net/webtoon/viewer_images.js?webtoon_episode_id=$episode_id";
		}
		$cmd = qq(wget.sh "$url" $encoding);
		#print $cmd . "\n";
		my $result = qx($cmd);
		if ($CHILD_ERROR != 0) {
			confess "Error: can't download the page html from '$url', $ERRNO\n";
			return -1;
		}
		my @img_file_arr = ();
		my @img_url_arr = ();
		my @img_size_arr = ();
		for my $line (split /}|\n/, $result) {
			if ($line =~ m!"url":"(http://[^"]+)",(?:(?:.*imageOrder)|(?:\s*$))!) {
				my $img_url = $1;
				if ($img_url !~ m!VodPlayer\.swf!) {
					print "<img src='$img_url' width='100%'/>\n";
				}
			}
		}
	}
}	


main();
