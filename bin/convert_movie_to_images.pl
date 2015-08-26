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


sub main
{
	my $link = $ARGV[0];
	my $id = get_md5_name($link);
	my $video_file = $id . ".avi";
	my $img_dir = $FEED_MAKER_WWW_FEEDS . "/img/thegoodmovie";
	my $img_url_prefix = "http://terzeron.net/xml/img/thegoodmovie";
	my $cmd;
	my $result;

	while (my $line = <STDIN>) {
		if ($line =~ m!<video src='[^']*videoPath=(rtmp://[^&]*)[^']*'>!) {
			my $movie_url = $1;
			if (not -e "${img_dir}/${id}_0001.jpg") { 
				if (not -e $video_file) {
					$cmd = qq(/Users/terzeron/workspace/rtmpdump/rtmpdump -q -r '$movie_url' > ${video_file});
					print "<!-- $cmd -->\n";
					$result = qx($cmd);
					print "<!-- $result -->";
				}
				
				$cmd = qq(/Users/terzeron/bin/extract_images_from_video.sh ${video_file} "${img_dir}/${id}_" > /dev/null 2>&1);
				print "<!-- $cmd -->\n";
				$result = qx($cmd);
				print "<!-- $result -->";
			}

			opendir(my $dh, $img_dir);
			while (my $file = readdir($dh)) {
				if ($file =~ m!${id}_\d+\.jpg$!x) {
					print "<img src='${img_url_prefix}/$file'/>\n";
				}
			}
			closedir($dh);

			#unlink($video_file);
		}
	}
}


main();
