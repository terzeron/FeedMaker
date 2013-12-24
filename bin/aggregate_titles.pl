#!/usr/bin/env perl

use English;
use warnings;
use strict;
use Modern::Perl;
use Carp;
use Encode;

use POSIX qw(strftime locale_h);
use Digest::MD5;
use File::Path;
use XML::RSS;
use FeedMaker;
use Text::Levenshtein qw(distance);
use Getopt::Std;


setlocale(LC_CTYPE, "ko_KR.utf8");
setlocale(LC_TIME, "C");
local $OUTPUT_AUTOFLUSH = 1;


sub print_usage
{
	print "Usage: $PROGRAM_NAME\t[ -t <threshold> ] <output file>\n";
	print "\n";
}


sub main
{
	my %opts = ();
	getopts("t:", \%opts);
	my $threshold = $opts{'t'};

	if (scalar @ARGV != 1) {
		print_usage();
		return -1;
	}

	my $output_file = $ARGV[0];
	my $temp_output_file = $output_file . ".temp";
	my $new_input_file = $output_file . ".input";
	my %linenum_link_map = ();
	my %duplicate_check_map = ();

	# split link and title into two separate files
	# and make line number & link mapping table
	if (not open(OUT1, "> $new_input_file")) {
		print STDERR "can't open file '$new_input_file' for reading, $ERRNO";
		return -1;
	}
	my $line_num = 1;
	while (my $line = <STDIN>) {
		if ($line =~ m!^\#!) {
			# skip comments
			next;
		}
		chomp $line;
		my ($link, $title) = split /\t/, $line;
		
		$linenum_link_map{$line_num} = $link . "\t" . $title;
		
		my $clean_title = $title;
		$clean_title =~ tr!A-Z!a-z!;
		$clean_title =~ s![\s\!-\/\:-\@\[-\`]*!!g;
		if (defined $duplicate_check_map{$clean_title} and exists $duplicate_check_map{$clean_title}) {
			next;
		} else {
			$duplicate_check_map{$clean_title} = 1;
		}			
		print OUT1 $title . "\n";
		$line_num++;
	}
	close(OUT1);

	# hierarchical clustering
	my $cluster_dir = $ENV{"FEED_MAKER_HOME"} . "/../hcluster";
	my $cmd = qq($cluster_dir/hcluster -t "$threshold" -s stop_words.txt "$new_input_file" "$temp_output_file");
	#print $cmd . "\n";
	my $result = qx($cmd);
	#print $result;

	# convert & extract temporary output file
	$cmd = qq(awk -F'\t' '\$2 >= 3 { for (i = 3; i < NF; i += 2) { print \$(i) FS \$(i + 1); } }' "$temp_output_file");
	if (not open(FILTER, "$cmd | ")) {
		print STDERR "can't execute the inline script '$cmd' for reading, $ERRNO";
		return -1;
	}
	if (not open(OUT2, "> $output_file")) {
		print STDERR "can't open file '$output_file' for reading, $ERRNO";
		return -1;
	}
	while (my $line = <FILTER>) {
		chomp $line;
		my ($linenum, $title) = split /\t/, $line;
		print OUT2 "$linenum_link_map{$linenum}\n";
	}
	close(FILTER);
	close(OUT2);
}

main();
