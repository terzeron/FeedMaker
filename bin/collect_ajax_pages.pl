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
		my $cmd = qq(wget.sh "$url" "$encoding");
		#print $cmd . "\n";
		my $result = `$cmd`;
        if ($CHILD_ERROR != 0) {
			confess "Error: can't get html from '$url'";
			return -1;
        }

        # write temporary file
        my $file_name = "literature_" . $article_num . "_" . $page_num . ".html";
        if (not open(OUT, "> $file_name")) {
            confess "can't open '$file_name' for writing, $ERRNO";
        }
        print OUT $result;
        close(OUT);

        # extract data
		$cmd = qq(extract_literature.py "$file_name");
        $result = `$cmd`;
        if ($CHILD_ERROR != 0 or $result eq "") {
            unlink($file_name);
            last;
        }
        unlink($file_name);

        print $result . "\n";

        $page_num++;
    }
}

main();
