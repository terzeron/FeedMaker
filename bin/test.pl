#!/usr/bin/env perl

use English;
use warnings;
use strict;

print $ARGV[0] . "\n";
print $ARGV[1] . "\n";
open(IN1, $ARGV[0]);
my %denied_feed_map = ();
while (my $feed = <IN1>) {
    chomp $feed;
    $denied_feed_map{$feed} = 1;
}
close(IN1);
open(IN2, $ARGV[1]);
while (my $line = <IN2>) {
	my ($date, $feed, $status) = split /\t/, $line;
    if (exists $denied_feed_map{$feed}) {
        next;
    }   
    print $feed . "\n";
}
close(IN2);
