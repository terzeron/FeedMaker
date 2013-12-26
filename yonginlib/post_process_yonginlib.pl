#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker;


sub main
{
	$ebook_flag = 0;
	while (my $line = <STDIN>) {
		chomp $line;
		if ($line =~ m!, 태블릿!) {
			$ebook_flag = 1;					
		}
	}

	if ($ebook_flag == 1) {
		
}


main();
