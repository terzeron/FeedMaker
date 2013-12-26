#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use Digest::MD5;
use FeedMaker qw(read_config get_md5_name);


sub get_cache_url
{
    my $img_url = shift;
    my $img_ext = shift;

    return "http://terzeron.net/xml/img/" . get_md5_name($img_url) . "." . $img_ext;
}


sub get_cache_file_name
{
    my $img_url = shift;
    my $img_ext = shift;

    return "/Users/terzeron/public_html/xml/img/" . get_md5_name($img_url) . "." . $img_ext;
}


sub download_image
{
	my $img_url = shift;
	my $img_ext = shift;
	my $page_url = shift;

	my $cache_file = get_cache_file_name($img_url, $img_ext);
	my $cmd = qq(wget.sh --download "$img_url" "$cache_file" "$page_url");
	#print $cmd . "\n";
	my $result = qx($cmd);
	if ($CHILD_ERROR != 0) {
		return -1;
	}
	return 0;
}


sub print_local_path
{
    my $img_url = shift;
    my $img_ext = shift;

    my $cache_url = get_cache_url($img_url, $img_ext);
    print "<img src='$cache_url' width='100%'/><br/>\n";
}


sub main
{
	my $img_prefix = "";
	my $img_index = -1;

	while (my $line = <STDIN>) {
		print $line;
	}

	my $config = ();
	my $config_file = "conf.xml";
	if (not read_config($config_file, \$config)) {
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
		for my $line (split /}|\n/, $result) {
        	if ($line =~ m!"url":"(http://[^"]+)",(?:(?:.*imageOrder)|(?:\s*$))!) {
				my $img_url = $1;
				if (download_image($img_url, "jpg", $url) < 0) {
					confess "Error: can't download the image from '$img_url', $ERRNO\n";
					last;
				}
				print_local_path($img_url, "jpg");
			}
        }
    }
}	


main();
