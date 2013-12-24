#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Modern::Perl;
use Carp;
use Encode;
use HTML::TreeBuilder::XPath;


sub main
{
	my $content = "";

	while (my $line = <STDIN>) {
		if ($line =~ m!^#!) {
			next;
		}
		$content .= $line;
	}

	my $tree = HTML::TreeBuilder::XPath->new;
	$tree->parse($content);
	my @anchors = $tree->findnodes('//a');
	for my $anchor (@anchors) {
		my $link = $anchor->{"href"};
		if ($link =~ m!^http://photo\.naver\.com!) {
			next;
		}
		my $title = $anchor->{"title"};
		if (not defined $title) {
			my $composed_title = "";
			# 타이틀이 없으면 하위 element를 탐색하여 타이틀을 구성함
			my $contents = $anchor->{"_content"};
			for my $content (@$contents) {
				if (defined $content and $content !~ m!^\s*$!) {
					# 타이틀이 존재하고 공백이 아니면
					#print "content=" . $content . "\n";
					if (UNIVERSAL::isa($content, 'HASH')) {
						my $sub_contents = $content->{"_content"};
						for my $sub_content (@$sub_contents) {
							if (UNIVERSAL::isa($sub_content, 'HASH')) {
								# 텍스트 사이 <br/> element 제거
								next;
							}
							#print "sub_content=" . $sub_content . "\n";
							$composed_title .= $sub_content;
						}
					}
				}
			}
			if ($composed_title ne "") {
				if ($link =~ m!^http://([^\.]+)\.blog\.me/(\d+)!) {
					$link = "http://m.blog.naver.com/PostView.nhn?blogId=$1&logNo=$2";
				}
				if ($link =~ m!^http://blog\.naver\.com/([^/]+)/(\d+)!) {
					$link = "http://m.blog.naver.com/PostView.nhn?blogId=$1&logNo=$2";
				}
				if ($link =~ m!^http://(kitchen.naver.com/theme/viewCook.nhn\?contentId.*)!) {
					$link = "http://m.$1";
				}
				print "$link\t$composed_title\n";
			}
		}
	}
}


main();
