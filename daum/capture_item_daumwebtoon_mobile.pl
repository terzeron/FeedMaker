#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;


sub main
{
	my $link = "";
	my $title = "";
	my $nickname = "";

	while (my $line = <STDIN>) {
		while ($line =~ m!"id":(\d+),"episode":(\d+),"title":"([^"]+)",!g) {
			printf("http://cartoon.media.daum.net/m/webtoon/viewer/%d\t%04d. %s\n", $1, $2, $3);
		}
	}
}


main();
