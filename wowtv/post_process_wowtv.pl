#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker;


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
	my $max_num_pages = 0;
	my $img_prefix = "";
	my $img_index = 0;
	my $img_index_len = 0;
	my $img_ext = "";
	my $page_url = $ARGV[0];

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!<(meta|style)!) {
			print $line;
		} elsif ($line =~ m!^(\d+)페이지</span>!) {
			if (int($1) > $max_num_pages) {
				$max_num_pages = int($1);
			}
		} elsif ($line =~ m!<img src='(http://[^\\]+)\\(\d+)\.(jpg|png|gif)'/>!) {
			$img_prefix = $1;
			$img_index = $2;
			$img_index_len = length($img_index);
			$img_ext = $3;
			#print "$img_prefix $img_index $img_ext\n";
			last;
		}
	}

	for (my $i = 1; $i <= $max_num_pages * 2; $i++) {
		my $img_url = sprintf("%s/%0" . $img_index_len . "d.%s", $img_prefix, $i, $img_ext);
		if (download_image($img_url, $img_ext, $page_url) < 0) {
			last;
		}
		my $cache_file = get_cache_file_name($img_url, $img_ext);
		my $cmd = qq(innercrop -f 4 -m crop ${cache_file} ${cache_file}.temp && mv -f  ${cache_file}.temp $cache_file);
		my $result = qx($cmd);
		if ($CHILD_ERROR != 0) {
			confess "can't crop the image file '$cache_file', $ERRNO\n";
			next;
		}
		print_local_path($img_url, $img_ext);
		#printf("<img src='%s/%0" . $img_index_len . "d.%s' width='100%%'>\n", $img_prefix, $i, $img_ext);
	}
}       


main();
