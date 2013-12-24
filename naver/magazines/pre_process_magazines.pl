#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Modern::Perl;
use FeedMaker;

sub main
{
	my @img_list = ();
	my @text_list = ();
	my @href_list = ();
	while (my $line = <STDIN>) {
		chomp $line;
		print $line . "\n";
		if ($line =~ m!bimgs\[\d+\] = \"(.+)\";!) {
			push @img_list, $1;
		} 
		if ($line =~ m!btxts\[\d+\] = \"(.+)\";!) {
			push @text_list, $1;
		}
		if ($line =~ m!bhrefs\[\d+\] = \"(.+)\";!) {
			push @href_list, $1;
		}
	}

	print "<div id='dynamic_data'>\n";
	print "<ul>\n";
	while (scalar @img_list > 0) {
		my $img = shift @img_list;
		my $href = shift @href_list;
		my $text = shift @text_list;
		print "<li><a href='" . $href . "'><img src='" . $img . "' /><br />" . $text . "</a><br /></li><br />\n";
	}
	print "</ul>\n";
	print "</div>\n";
}


main();
