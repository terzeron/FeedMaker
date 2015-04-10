#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use Digest::MD5;
use FeedMaker qw(read_config get_md5_name);


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
		} elsif ($line =~ m!<img src='http://(\w+\.ohmynews\.com)/([^']+)\.(jpg|gif)!gi) {
			$img_host = $1;
			$img_path = $2;
			$img_ext = $3;
			print "<img src='http://${img_host}/${img_path}.${img_ext}' width='100%'/>\n";
		}
		#print $line . "\n";
	}
	#print "img_path=$img_path, img_index=$img_index\n";
}	


main();
