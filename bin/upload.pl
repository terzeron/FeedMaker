#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Getopt::Long;


sub main
{
    my $dir = "/Users/terzeron/public_html/xml";
    my @data_file_list = ();
	my $do_upload = 0;
	my $max_try_count = 3;
	my $rss_file = shift @ARGV;

	if (-f "$rss_file.old") {
		# 과거 파일이 존재하면 비교해보고 다른 경우에만 업로드
		my $cmd = qq(diff "$rss_file" "$rss_file".old | grep -v -Ee \"(^(<|>) <(pubDate|lastBuildDate))|(^---\$)|(^[0-9,]+[a-z][0-9,]+\$)\" | wc -c);
		print "$cmd\n";
		my $result = qx($cmd);
		print $result;
		chomp $result;
		if ($result =~ /^\s*(\d+)\s*$/ and $1 ne "0") {
			$do_upload = 1;
		}
	} elsif (-f $rss_file) {
		# 과거 파일이 존재하지 않고 신규 파일만 존재하면 업로드
		$do_upload = 1;	
	} else {
		confess "Error: can't upload the RSS file, $ERRNO, ";
		return -1;
	}
		
	if ($do_upload == 1) {
		my $cmd = "cp $rss_file $dir";
		print "$cmd\n";
		for (my $i = 0; $i < $max_try_count; $i++) {
			my $result = `$cmd`;
			print $result;
			if ($CHILD_ERROR == 0) {
				print "Upload: success!\n";
				return 0;
			}
		}
	} else {
		print "Upload: No change from the previous RSS file\n";
		return -1;
	}
}


exit main();
