#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;
use Getopt::Std;


sub print_usage
{
	print "usage:\t$PROGRAM_NAME [ -n <limit of recent feeds> ]\n";
	print "\n";
	exit(-1);
}


sub main
{
	my $link = "";
	my $title = "";
	my $url_prefix = "";
	my $cartoon_id = 0;
	my $episode_id = 0;
	my $episode_num = 0;
	my $state = 0;

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
		if ($state == 0) {
			if ($line =~ m!document\.location\.href\s*=\s*"([^"]+)"!) {
				$url_prefix = $1;
				$state = 1;
			}
		} elsif ($state == 1) {
			while ($line =~ m!<option value='(\d+)\|(\d+)'(?: selected)?>(.+?(\([^\)]+\))?)</option>!g) {
				$cartoon_id = $1;
				$episode_id = $2;
				$title = $3;
				$episode_num = $4;
				#$title .= "(" . $episode_num . ")";
				$link = "http://sports.khan.co.kr/" . $url_prefix . $cartoon_id . "&page=" . $episode_id;
				$link =~ s!&amp;!&!g;
				print "$link\t$title\n";
				$count++;
				if ($count >= $limit_feeds) {
					last;
				}
			}
		}
	}
}


main();
