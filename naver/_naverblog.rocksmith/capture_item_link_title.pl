#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use URI::Encode qw(uri_decode);


sub main
{
	my $link = "";
	my $title = "";

	while (my $line = <STDIN>) {
		while ($line =~ m!{"logNo":"(\d+)","title":"([^"]+)",!g) {
			my $logno = $1;
			$title = uri_decode($2);
			$title =~ s/\+/ /g;
			$title =~ s/&quot;/'/g;
			$link = "http://blog.naver.com/PostView.nhn?blogId=escaflowne&logNo=" . $logno . "&categoryNo=55&parentCategoryNo=0&viewDate=&postListTopCurrentPage=1&userTopListOpen=true&userTopListCount=5&userTopListManageOpen=false";
			print "$link\t$title\n";
		}
	}
}


main();
