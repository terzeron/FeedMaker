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
	#print $result;
	if ($CHILD_ERROR != 0) {
		confess "can't download image file '$img_url', $ERRNO\n";
		return -1;
	}    
	sleep(1);
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
	my $img_prefix = "";
	my $img_index = -1;
	my $img_ext = "jpg";
	my $img_url = "";
	my $cache_url = "";
	my $cache_file = "";
	my $page_url = $ARGV[0];
	my $num_units = 5;

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!<(meta|style)!) {
			print $line . "\n";
		} elsif ($line =~ m!<img src='(http://webtoon\.olleh\.com/download/webtoon/[^']+)\.(jpg|gif|png)'!gi) {
			$img_prefix = $1;
			$img_ext = $2;
			$img_url = $img_prefix . "." . $img_ext;
			# 이미지 다운로드
			if (download_image($img_url, $img_ext, $page_url) < 0) {
				confess "Error: can't download the image from '$img_url', $ERRNO\n";
				last;
			}
			print_local_path($img_url, $img_ext);
		}
	}
}	


main();
