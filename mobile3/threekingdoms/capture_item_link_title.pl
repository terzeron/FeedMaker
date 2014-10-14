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
	my $num = 1;
  
	while (my $line = <STDIN>) {
		while ($line =~ m! href="(?<link>[^"]+)-1/?" title="(?<title>[^"]+)"!g) {
			$link = $+{"link"} . "-1&dummy=1";
			$title = $num . " " . $+{"title"} . "-1";
			$link =~ s!&amp;!&!g;
			print "$link\t$title\n";
			$num++;

			for (my $i = 2; $i < 20; $i++) {
				$link = $+{"link"} . "-" . $i;
				my $cmd = qq(wget.sh --try $link);
				my $result = qx($cmd);
				if ($CHILD_ERROR != 0) {
					last;
				}
				$title = $num . " " . $+{"title"} . "-" . $i;
				$link =~ s!&amp;!&!g;
				$link .= "&dummy=1";
				print "$link\t$title\n";
				$num++;
			}
		}
	}
}

main();
