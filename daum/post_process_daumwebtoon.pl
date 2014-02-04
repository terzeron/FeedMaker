#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use Digest::MD5;
use FeedMaker qw(read_config get_md5_name);
use Getopt::Std;


sub get_cache_url
{
	my $img_url = shift;
	my $img_ext = shift;
	my $url_prefix = "http://terzeron.net/xml/img";

	if ($img_url =~ m!^http://! and defined $img_ext) {
		return $url_prefix . "/" . get_md5_name($img_url) . "." . $img_ext;
	}
	return $url_prefix . "/" . $img_url;
}


sub get_cache_file_name
{
	my $img_url = shift;
	my $img_ext = shift;
	my $path_prefix = "/Users/terzeron/public_html/xml/img";

	if ($img_url =~ m!^http://! and defined $img_ext) {
		return $path_prefix . "/" . get_md5_name($img_url) . "." . $img_ext;
	} 
	return $path_prefix . "/" . $img_url;
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
	my $img_ext = "jpg";
	my $num_units = 25;

	my %opts = ();
	my $opt_str = "c:";
	my $bgcolor_option = "";
	our $opt_n;
	getopts($opt_str, \%opts);
	if (defined $opts{"c"}) {
		if ($opts{"c"} =~ m!^(white|black)$!) {
			$bgcolor_option = "-c " . $opts{"c"};
		}
	}

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
				#print $img_url . "\n";
				# download
				if (download_image($img_url, $img_ext, $url) < 0) {
					confess "Error: can't download the image from '$img_url', $ERRNO\n";
					last;
				}

				my $cache_file = get_cache_file_name($img_url, $img_ext);
				push @img_file_arr, $cache_file;
				push @img_url_arr, $img_url;
				$cmd = qq(../../../CartoonSplit/size.py ${cache_file});
				$result = qx($cmd);
				if ($result =~ m!^(\d+)\s+(\d+)$!) {
					my $width = $1;
					my $height = $2;
					push @img_size_arr, "$width\t$height";
					#print "cache_file=$cache_file, img_url=$img_url, width=$width, height=$height\n";
				}
			}
		}

		# calculate the total height
		my $total_height = 0;
		for my $dimension (@img_size_arr) {
			my ($width, $height) = split /\t/, $dimension;
			$total_height += $height;
		}
		#print "total_height=$total_height\n";
		if ($total_height > 65500) {
			# no merge mode
			for my $img_url (@img_url_arr) {
				print_local_path($img_url, $img_ext);
			}
		} else {
			# merge mode
			my $merged_img_file = get_cache_file_name($post_link, $img_ext);
			$cmd = qq(../../../CartoonSplit/merge.py ${merged_img_file} );
			for my $cache_file (@img_file_arr) {
				$cmd .= $cache_file . " ";
			}
			#print "$cmd\n";
			$result = qx($cmd);
			#print $result;
			if ($CHILD_ERROR != 0) {
				confess "Error: can't merge the image files, $ERRNO\n";
				return -1;
			}
			
			# remove the original image
			$cmd = qq(rm -f );
			for my $cache_file (@img_file_arr) {
				$cmd .= $cache_file . " ";
			}
			#print "$cmd\n";
			$result = qx($cmd);
			#print $result;
			
			# split
			$cmd = qq(../../../CartoonSplit/split.py -n ${num_units} -b 10 ${bgcolor_option} ${merged_img_file});
			#print "$cmd\n";
			$result = qx($cmd);
			#print $result;
			if ($CHILD_ERROR != 0) {
				confess "Error: can't split the image file, $ERRNO\n";
				return -1;
			}
			
			# remove the merged image
			$cmd = qq(rm -f $merged_img_file);
			#print "$cmd\n";
			$result = qx($cmd);
			#print $result;
			
			# print the split images
			for (my $i = 1; $i <= $num_units; $i++) {
				my $split_img_file = get_cache_file_name(get_md5_name($post_link) . "." . $i . "." . $img_ext);
				if (-e $split_img_file) {
					my $split_img_url = get_cache_url(get_md5_name($post_link) . "." . $i . "." . $img_ext);
					print "<img src='${split_img_url}' width='100%'/>\n";
				} else {
					last;
				}
			}
		}
	}
}	


main();
