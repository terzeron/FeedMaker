#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use Digest::MD5;
use FeedMaker qw(get_md5_name);
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
		return $url_prefix . "/" . get_md5_name($img_url) . $postfix_str . $index_str . "." . $img_ext;
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
		return $path_prefix . "/" . get_md5_name($img_url) . $postfix_str . $index_str . "." . $img_ext;
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
	#print "<!-- $cmd -->\n";
	my $result = qx($cmd);
	#print "<!-- $result -->\n";
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

	my $url = $ARGV[0];
	my $cmd = "";
	my $result = "";

	mkpath($path_prefix);

	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!(.*)<img src=(?:["'])([^"']+)(?:["']) width='\d+%?'/?>(.*)!) {
			my $pre_text = $1;
			my $img_url = $2;
			my $post_text = $3;

			if ($pre_text !~ m!^\s*$!) {
				print $pre_text . "\n";
			}

			# download
			if (download_image($path_prefix, $img_url, $img_ext, $url) < 0) {
				#confess "Error: can't download the image from '$img_url', $ERRNO\n";
				next;
			}
			
			my $cache_file = get_cache_file_name($path_prefix, $img_url, $img_ext);
			my $cache_url = get_cache_url($img_url_prefix, $img_url, $img_ext);
			#print "<!-- $img_url -> $cache_file / $cache_url -->\n";
			print "<img src='$cache_url'/>\n";

			if ($post_text !~ m!^\s*$!) {
				print $post_text . "\n";
			}
		} else {
			print $line . "\n";
		}
	}
}


main();
