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
	return 0;
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
	my $num_units = 4;

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!<(meta|style)!) {
			print $line . "\n";
		} elsif ($line =~ m!<img src='(http://(?:ucfile\d+\.nate\.com|crayondata\.cyworld\.com)/new_contents[^']+)\.(jpg|gif)'!gi) {
			$img_prefix = $1;
			$img_ext = $2;
			$img_url = $img_prefix . "." . $img_ext;
			# 이미지 다운로드
			if (download_image($img_url, $img_ext, $page_url) < 0) {
				confess "Error: can't download the image from '$img_url', $ERRNO\n";
				last;
			}
			$cache_url = get_cache_url($img_url, $img_ext);
			# 이미지 분할
			$cache_file = get_cache_file_name($img_url, $img_ext);
			my $cmd = qq(../../../CartoonSplit/split.py -n $num_units -b 20 $cache_file);
			#print $cmd . "\n";
			my $result = qx($cmd);
			#print $result;
			if ($CHILD_ERROR != 0) {
				# 분할되지 않은 로컬 이미지 파일의 url을 출력
				print "<img src='$cache_url' width='100%'/><br/>\n";
			} else {
				# 원본 이미지 파일 삭제
				$cmd = qq(rm -f $cache_file);
				$result = qx($cmd);

				# 새로운 이미지 경로 출력
				$cache_url =~ m!^(.+)\.(jpg|gif)$!;
				my $split_img_url_prefix = $1;
				my $split_img_url_ext = $2;
				$cache_file =~ m!^(.+)\.(jpg|gif)$!;
				my $split_img_file_prefix = $1;
				my $split_img_file_ext = $2;
				for (my $i = 1; $i <= $num_units; $i++) {
					my $split_img_url = $split_img_url_prefix . "." . $i . "." . $split_img_url_ext;
					my $split_img_file = $split_img_file_prefix . "." . $i . "." . $split_img_file_ext;
					if (not -e $split_img_file) {
						last;
					}
					print "<img src='$split_img_url' width='100%'/><br/>\n";
				}
			}
		}
		#print $line . "\n";
	}
	#print "img_prefix=$img_prefix, img_index=$img_index\n";
}	


main();
