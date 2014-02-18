#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use Digest::MD5;
use FeedMaker qw(get_md5_name);
use Getopt::Std;


sub get_cache_url
{
	my $img_url = shift;
	my $img_ext = shift;
	my $postfix = shift;
	my $index = shift;
	my $url_prefix = "http://terzeron.net/xml/img";

	my $postfix_str = "";
	if (defined $postfix and $postfix ne "") {
		$postfix_str = "_" . $postfix;
	}
	my $index_str = "";
	if (defined $index and $index ne "") {
		$index_str = "." . $index;
	}
	if ($img_url =~ m!^http://! and defined $img_ext) {
		return $url_prefix . "/" . get_md5_name($img_url) . $postfix_str . $index_str . "." . $img_ext;
	}
	return $url_prefix . "/" . $img_url;
}


sub get_cache_file_name
{
	my $img_url = shift;
	my $img_ext = shift;
	my $postfix = shift;
	my $index = shift;
	my $path_prefix = "/Users/terzeron/public_html/xml/img";

	my $postfix_str = ""; 
    if (defined $postfix and $postfix ne "") {
        $postfix_str = "_" . $postfix;
    }
    my $index_str = "";
    if (defined $index and $index ne "") {
        $index_str = "." . $index;
    }                     
	if ($img_url =~ m!^http://! and defined $img_ext) {
		return $path_prefix . "/" . get_md5_name($img_url) . $postfix_str . $index_str . "." . $img_ext;
	} 
	return $path_prefix . "/" . $img_url;
}


sub download_image
{
	my $img_url = shift;
	my $img_ext = shift;
	my $page_url = shift;

	my $cache_file = get_cache_file_name($img_url, $img_ext);
	my $cmd = qq([ -f "$cache_file" ] || wget.sh --download "$img_url" "$cache_file" "$page_url");
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
		if ($opts{"c"} =~ m!^(white|black|blackorwhite)$!) {
			$bgcolor_option = "-c " . $opts{"c"};
		}
	}

	my $url = $ARGV[0];
	my @img_file_arr = ();
	my @img_url_arr = ();
	my @img_size_arr = ();
	my $cmd = "";
	my $result = "";

	while (my $line = <STDIN>) {
		if ($line =~ m!<img src=(?:["'])([^"']+)(?:["']) width='\d+%'/?>!) {
			my $img_url = $1;
			#print $img_url . "\n";
			# download
			if (download_image($img_url, $img_ext, $url) < 0) {
				#confess "Error: can't download the image from '$img_url', $ERRNO\n";
				next;
			}
			
			my $cache_file = get_cache_file_name($img_url, $img_ext);
			push @img_file_arr, $cache_file;
			push @img_url_arr, $img_url;
			#print "$img_url --> $cache_file\n";
			$cmd = qq(../../../CartoonSplit/size.py ${cache_file});
			#print "$cmd\n";
			$result = qx($cmd);
			if ($CHILD_ERROR != 0) {
				confess "Error: can't get the size of image file '${cache_file}', cmd='$cmd'\n";
				return -1;
			}
			if ($result =~ m!^(\d+)\s+(\d+)$!) {
				my $width = $1;
				my $height = $2;
				push @img_size_arr, "$width\t$height";
				#print "cache_file=$cache_file, img_url=$img_url, width=$width, height=$height\n";
			}
		}
	}

	if (scalar @img_file_arr > 0) {
		# calculate the total height
		my $total_height = 0;
		for my $dimension (@img_size_arr) {
			my ($width, $height) = split /\t/, $dimension;
			$total_height += $height;
		}
		#print "total_height=$total_height\n";
		my @img_file_arr1 = ();
		my @img_file_arr2 = ();
		if ($total_height > 65500) {
			# split array into two sub-array
			my $half = int((scalar @img_file_arr) / 2); 
			#print "length=" . (scalar @img_file_arr) . " half=$half\n";
			@img_file_arr1 = splice @img_file_arr, 0, $half;
			@img_file_arr2 = splice @img_file_arr, 0;
		}  else {
			@img_file_arr1 = @img_file_arr;
			@img_file_arr2 = ();
		}
		#print scalar @img_file_arr1 . "\n";
		#print scalar @img_file_arr2 . "\n";

		my $num = 1;
		foreach my $img_file_arr_ref (\@img_file_arr1, \@img_file_arr2) {
			my @img_file_arr = @$img_file_arr_ref;
			if (scalar @img_file_arr == 0) {
				next;
			}
			# merge mode
			my $merged_img_file = get_cache_file_name($url, $img_ext, $num);
			$cmd  = qq(../../../CartoonSplit/merge.py ${merged_img_file} );
			for my $cache_file (@img_file_arr) {
				$cmd .= $cache_file . " ";
			}
			#print "$cmd\n";
			$result = qx($cmd);
			#print $result;
			if ($CHILD_ERROR != 0) {
				confess "Error: can't merge the image files, cmd='$cmd'\n";
				return -1;
			}
				
			# remove the original image
			$cmd = qq(rm -f );
			for my $cache_file (@img_file_arr) {
				$cmd .= $cache_file . " ";
			}
			#print "$cmd\n";
			#$result = qx($cmd);
			#print $result;
				
			# split
			$cmd = qq(../../../CartoonSplit/split.py -n ${num_units} -b 10 ${bgcolor_option} ${merged_img_file});
			#print "$cmd\n";
			$result = qx($cmd);
			#print $result;
			if ($CHILD_ERROR != 0) {
				confess "Error: can't split the image file, cmd='$cmd'\n";
				return -1;
			}
				
			# remove the merged image
			$cmd = qq(rm -f $merged_img_file);
			#print "$cmd\n";
			#$result = qx($cmd);
			#print $result;
				
			# print the split images
			for (my $i = 1; $i <= $num_units; $i++) {
				my $split_img_file = get_cache_file_name($url, $img_ext, $num, $i);
				if (-e $split_img_file) {
					my $split_img_url = get_cache_url($url, $img_ext, $num, $i);
					print "<img src='${split_img_url}' width='100%'/>\n";
				} else {
					last;
				}
			}
			$num++;
		}
	}	
}


main();
