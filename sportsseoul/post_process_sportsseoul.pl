#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker;

use Scalar::Util qw(reftype looks_like_number);
use JSON qw(decode_json);


sub main
{
	my $url = $ARGV[0];
	my $data_url_prefix = "http://www.sportsseoul.com/cartoon/ajaxData.ss?cm_id=";
	my $img_url_prefix = "";
	my $img_ext = "";
	my $num = 0;
	if ($url =~ m!http://.*cm_id=([^&]+)&cm_cnt=(\d+)!) {
		my $id = $1;
		my $index = $2;
		my $cmd = qq(wget.sh "$data_url_prefix$id&cm_cnt=$index" utf8);
		my $result = qx($cmd);
		my $data = decode_json($result);
		if (defined $data and reftype($data) eq "ARRAY") {
			my $map_ref = $data->[0];
			if (exists $map_ref->{"cd_data"}) {
				my $url_arr_str = $map_ref->{"cd_data"};
				while ($url_arr_str =~ m!"(http://[^"]+/)(\d+|\w+)\.(jpg|jpeg|gif|png)"!gi) {
					$img_url_prefix = $1;
					$num = $2;
					$img_ext = $3;
					print "<img src='" . $img_url_prefix . $num . "." . $img_ext . "' width='100%'/>\n";
				}	
				if (looks_like_number($num)) {
					for (my $i = $num + 1; $i < 20; $i++) {
						my $url = $img_url_prefix . $i . "." . $img_ext;
						my $cmd = qq(wget.sh --try "$url");
						my $result = qx($cmd);
						if ($CHILD_ERROR != 0) {
							last;
						}
						print "<img src='" . $url . "' width='100%'/>\n";
					}
				}
			}
		}
	}
}


main();
