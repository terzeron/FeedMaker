#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use Digest::MD5;
use FeedMaker;
use Getopt::Std;
use File::Path;
use Cwd;
use Env qw(FEED_MAKER_WWW_FEEDS);


sub get_cache_url
{
	my $url_prefix = shift;
	my $img_url = shift;
	my $img_ext = shift;
	my $postfix = shift;
	my $index = shift;

	my $postfix_str = "";
	if (defined $postfix and $postfix ne "") {
		$postfix_str = "_" . $postfix;
	}
	my $index_str = "";
	if (defined $index and $index ne "") {
		$index_str = "." . $index;
	}
	if ($img_url =~ m!^http://! and defined $img_ext) {
		return $url_prefix . "/" . FeedMaker::getMd5Name($img_url) . $postfix_str . $index_str . "." . $img_ext;
	}
	return $url_prefix . "/" . $img_url;
}


sub get_cache_file_name
{
	my $path_prefix = shift;
	my $img_url = shift;
	my $img_ext = shift;
	my $postfix = shift;
	my $index = shift;

	my $postfix_str = ""; 
    if (defined $postfix and $postfix ne "") {
        $postfix_str = "_" . $postfix;
    }
    my $index_str = "";
    if (defined $index and $index ne "") {
        $index_str = "." . $index;
    }                     
	if ($img_url =~ m!^http://! and defined $img_ext) {
		return $path_prefix . "/" . FeedMaker::getMd5Name($img_url) . $postfix_str . $index_str . "." . $img_ext;
	} 
	return $path_prefix . "/" . $img_url;
}


sub download_image
{
	my $path_prefix = shift;
	my $img_url = shift;
	my $img_ext = shift;
	my $page_url = shift;

	my $cache_file = get_cache_file_name($path_prefix, $img_url, $img_ext);
	my $cmd = qq([ -f "$cache_file" -a -s "$cache_file" ] || wget.sh --download "$cache_file" --referer "$page_url" "$img_url");
	#print $cmd . "\n";
	my $result = qx($cmd);
	#print $result;
	if ($CHILD_ERROR != 0) {
		return -1;
	}
	return 0;
}


sub main
{
	my $cwd = getcwd;
	my $feed_name = qx(basename $cwd);
	chomp $feed_name;
	my $img_url_prefix = "http://terzeron.net/xml/img/$feed_name";
	my $path_prefix = $FEED_MAKER_WWW_FEEDS . "/img/$feed_name";

	my $img_prefix = "";
	my $img_index = -1;
	my $img_ext = "jpg";
	my $num_units = 25;

	my %opts = ();
	my $opt_str = "c:i";
	my $bgcolor_option = "";
	my $do_innercrop = 0;
	our $opt_n;
	getopts($opt_str, \%opts);
	if (defined $opts{"c"}) {
		if ($opts{"c"} =~ m!^(\w+)$!) {
			$bgcolor_option = "-c " . $opts{"c"};
		}
	} 
	if (defined $opts{"i"}) {
		$do_innercrop = 1;
	}

	my $url = $ARGV[0];
	my @img_file_arr = ();
	my @img_url_arr = ();
	my @img_size_arr = ();
	my $cmd = "";
	my $result = "";

	mkpath($path_prefix);

	while (my $line = <STDIN>) {
		if ($line =~ m!<img src=(?:["'])([^"']+)(?:["']) width='\d+%?'/?>!) {
			my $img_url = $1;
			#print $img_url . "\n";
			# download
			if (download_image($path_prefix, $img_url, $img_ext, $url) < 0) {
				#confess "Error: can't download the image from '$img_url', $ERRNO\n";
				next;
			}
			
			my $cache_file = get_cache_file_name($path_prefix, $img_url, $img_ext);
			push @img_file_arr, $cache_file;
			push @img_url_arr, $img_url;
			#print "<!-- $img_url -> $cache_file -->\n";
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
				#print "<!-- cache_file=$cache_file, img_url=$img_url, width=$width, height=$height -->\n";
			}
		} else {
			print $line . "\n";
		}
	}

	if (scalar @img_file_arr > 0) {
		# calculate the total height
		my $total_height = 0;
		for my $dimension (@img_size_arr) {
			my ($width, $height) = split /\t/, $dimension;
			$total_height += $height;
		}
		print "<!-- total_height=$total_height -->\n";
		my @img_file_arr1 = ();
		my @img_file_arr2 = ();
		my @img_file_arr3 = ();
		my @img_file_arr4 = ();
		# split array into 4 sub-array
		my $part = int((scalar @img_file_arr + 3) / 4); 
		print "<!-- length=" . (scalar @img_file_arr) . " part=$part -->\n";
		@img_file_arr1 = splice @img_file_arr, 0, $part;
		@img_file_arr2 = splice @img_file_arr, 0, $part;
		@img_file_arr3 = splice @img_file_arr, 0, $part;
		@img_file_arr4 = splice @img_file_arr, 0, $part;
		print "<!-- part1=" . (scalar @img_file_arr1) . ", part2=" . (scalar @img_file_arr2) . ", part3=" . (scalar @img_file_arr3) . ", part4=" . (scalar @img_file_arr4) . " -->\n";

		my $num = 1;
		foreach my $img_file_arr_ref (\@img_file_arr1, \@img_file_arr2, \@img_file_arr3, \@img_file_arr4) {
			my @img_file_arr = @$img_file_arr_ref;
			if (scalar @img_file_arr == 0) {
				next;
			}
			# merge mode
			my $merged_img_file = get_cache_file_name($path_prefix, $url, $img_ext, $num);
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

			# crop mode (optional)
			if ($do_innercrop == 1) {
				$cmd = qq(innercrop -f 4 -m crop ${merged_img_file} ${merged_img_file}.temp && mv -f ${merged_img_file}.temp ${merged_img_file});
				#print "$cmd\n";
                $result = qx($cmd);
                if ($CHILD_ERROR != 0) {
					confess "can't crop the image file '$merged_img_file', cmd='$cmd'\n";
					return -1;
				}
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
				confess "Error: can't split the image file, cmd='$cmd'\n";
				return -1;
			}
				
			# remove the merged image
			$cmd = qq(rm -f $merged_img_file);
			#print "$cmd\n";
			$result = qx($cmd);
			#print $result;
				
			# print the split images
			for (my $i = 1; $i <= $num_units; $i++) {
				my $split_img_file = get_cache_file_name($path_prefix, $url, $img_ext, $num, $i);
				if (-e $split_img_file) {
					my $split_img_url = get_cache_url($img_url_prefix, $url, $img_ext, $num, $i);
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
