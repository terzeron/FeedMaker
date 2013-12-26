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
	print "<img src='$cache_url' width='100%'/>\n";
}


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
			$img_url = "http://" . $img_host . "/" . $img_path . $img_index . "." . $img_ext;
			if (download_image($img_url, $img_ext, $page_url) < 0) {
				confess "Error: can't download the image from '$img_url', $ERRNO\n";
				last;
			}
			print_local_path($img_url, $img_ext);
		} elsif ($line =~ m!<img src='http://(imgcomic.naver.(?:com|net))/([^']+)\.(jpg|gif)!gi) {
			$img_host = $1;
			$img_path = $2;
			$img_ext = $3;
			$img_url = "http://" . $img_host . "/" . $img_path . "." . $img_ext;
			if (download_image($img_url, $img_ext, $page_url) < 0) {
				confess "Error: can't download the image from '$img_url', $ERRNO\n";
				last;
			}
			print_local_path($img_url, $img_ext);
		}
		#print $line . "\n";
	}
	#print "img_path=$img_path, img_index=$img_index\n";

	my $config = ();
	my $config_file = "conf.xml";
	if (not read_config($config_file, \$config)) {
		confess "Error: can't read configuration!, ";
		return -1;
	}
	my $extraction_config = $config->{"extraction"};
	my $encoding = $extraction_config->{"encoding"};
	if (not defined $encoding) {
		$encoding = "utf8";
	}
	
	if ($img_path ne "" and $img_index >= 0) {
		# add some additional images loaded dynamically
		for (my $i = int($img_index) + 1; $i < 50; $i++) {
			#my $format = "%1" . length($img_index) . "d";
			#my $img_url = $img_path . sprintf($format, $i) . "." . $img_ext;
			$img_url = "http://" . $img_host . "/" . $img_path . $i . "." . $img_ext;
			if (download_image($img_url, $img_ext, $page_url) < 0) {
				last;
			}
			print_local_path($img_url, $img_ext);
		}
	}
}	


main();
