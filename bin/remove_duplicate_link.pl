#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;

use HTML::Parser;
use FeedMaker;


sub remove_duplicates
{
    my $ref = shift;
    my @list = @$ref;
    #print "# remove_duplicates()\n";

    my %hash = map { $_, 1 } @list;
    return keys %hash;
}


sub main
{
	my $output_file = $ARGV[0];
	my @total_list = ();

	while (my $line = <STDIN>) {
		if ($line =~ m!^\#!) {
			# skip comments
			next;
		}
		chomp $line;
		push @total_list, $line;
	}

	@total_list = remove_duplicates(\@total_list);

	if (not open(OUT, "> $output_file")) {
        confess "Error: can't open file '$output_file' for writing, $ERRNO,";
        return -1;
    }
	foreach my $item (sort @total_list) {
		print OUT $item . "\n";
	}
	close(OUT);

	return 0;
}

main();
