#!/usr/bin/env perl

package FeedMaker;


use English;
use warnings;
use strict;
use Modern::Perl;
use Test::More;
use FeedMaker;


sub xmlEscapeTest
{
    my $str;
    $str = FeedMaker::xmlEscape("한글");
    ok($str eq decode("utf-8", "<![CDATA[한글]]>"));
    $str = FeedMaker::xmlEscape("english text");
    ok($str eq "<![CDATA[english text]]>");
}


sub readConfigTest
{
    my $config = readConfig();
    ok(defined $config->{"collection"} and defined $config->{"extraction"} and defined $config->{"rss"});
}


sub getConfigValueTest
{
    my $config = readConfig();
    my @path = ("collection", "use_url_pattern");
    my $config_value;

    $config_value = FeedMaker::getConfigValue($config, 1, "", ("extraction", "element_list", "element_id"));
    ok($config_value eq "ct");
    $config_value = FeedMaker::getConfigValue($config, 1, "", ("collection", "list_url_list", "list_url"));
    ok($config_value eq "http://m.navercast.naver.com/homeMain.nhn?page=");
    $config_value = FeedMaker::getConfigValue($config, 0, "utf8", ("collection", "encoding"));
    ok($config_value eq "utf8");
}


sub main
{
    xmlEscapeTest();
    readConfigTest();
    getConfigValueTest();
    done_testing();
}


main();
