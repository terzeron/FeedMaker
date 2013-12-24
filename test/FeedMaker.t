#!/usr/bin/env perl

package FeedMaker;


use English;
use warnings;
use strict;
use Modern::Perl;
use Test::More;
use FeedMaker;


sub xml_escape_test
{
	my $str;
	$str = xml_escape("한글");
	ok($str eq decode("utf-8", "<![CDATA[한글]]>"));
	$str = xml_escape("english text");
	ok($str eq "<![CDATA[english text]]>");
}


sub read_config_test
{
	my $config_file = shift;
	my $config = read_config($config_file);
	ok(defined $config->{"collection"} and defined $config->{"extraction"} and defined $config->{"rss"});
}


sub get_config_value_test
{
	my $config_file = shift;
	my $config = read_config($config_file);
	my @path = ("collection", "use_url_pattern");
	my $config_value;

	$config_value = get_config_value($config, 1, ("extraction", "element_list", "element_id"));
	ok($config_value eq "ct");
	$config_value = get_config_value($config, 1, ("collection", "list_url_list", "list_url"));
	ok($config_value eq "http://m.navercast.naver.com/homeMain.nhn?page=");
	$config_value = get_config_value($config, 0, ("collection", "encoding"));
	ok($config_value eq "");
}


sub main
{
	my $test_config_file = "test.config.xml";
	xml_escape_test();
	read_config_test($test_config_file);
	get_config_value_test($test_config_file);
	done_testing();
}


main();
