#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;


sub main
{
	my $leaf_id = $ARGV[0];
    my $article_num = $ARGV[1];
    my $page_num = $ARGV[2];
	my $encoding = $ARGV[3];

    while (1) {
        my $url = "http://navercast.naver.com/ncc_request.nhn?url=http://data.navercast.naver.com/literature_module/" . $leaf_id . "/literature_" . $article_num . "_" . $page_num . ".html";

		my $cmd = qq(wget.sh "$url" | extract_literature.py);
		#print $cmd . "\n";
		my $result = qx($cmd);
        if ($CHILD_ERROR != 0) {
			confess "Error: can't get html from '$url'";
			return -1;
        }
        print $result . "\n";

        $page_num++;
    }
}

main();
