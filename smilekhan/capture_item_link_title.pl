#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use Getopt::Std;


sub print_usage
{
	print "usage:\t$PROGRAM_NAME [ -n <limit of recent feeds> ] conf.xml\n";
	print "\n";
	exit(-1);
}


sub main
{
	my $link = "";
	my $title = "";

	my %opts = ();                                                              
    my $opt_str = "n:";                                                         
    my $limit_feeds = 10000;                                                    
    our $opt_n;                                                                 
    getopts($opt_str, \%opts);                                                  
    if (defined $opts{"n"}) {                                                   
        if ($opts{"n"} =~ m!^\s*\d+\s*$!) {                                     
            $limit_feeds = $opts{"n"};                                          
        } else {                                                                
            print_usage();                                                      
        }                                                                       
    }                                                                           

	my $count = 0;
	while (my $line = <STDIN>) {
		while ($line =~ m!<li><a href="/(cartoon/index\.html\?category=\d+&artid=\d+)">(?:<b>)?([^<]+)(?:</b>)?</a></li>!) {
			$link = "http://smile.khan.co.kr/" . $1;
			$title = $2;
			$link =~ s!&amp;!&!g;
			print "$link\t$title\n";
			$count++;
			if ($count >= $limit_feeds) {
				last;
			}
		}
	}
}


main();
