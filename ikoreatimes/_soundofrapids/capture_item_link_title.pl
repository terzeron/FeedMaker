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
  
	while (my $line = <STDIN>) {
		if ($line =~ m!<a href="(view.aspx[^"]*)"[^>]*ViewLink[^>]*>(?:(?:• )?\[황석영 연재소설\] )?([^<]+)</a>!) {
			$link = "http://www.ikoreatimes.com/Article/" . $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			$title =~ s!&(lt|gt);!!g;
			print "$link\t$title\n";
		}
	}
}

main();
