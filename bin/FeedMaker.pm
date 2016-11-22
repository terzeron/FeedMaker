#!/usr/bin/env perl

package FeedMaker;

use base 'Exporter';
our @EXPORT = qw(readConfig getConfigValue printAllHashItems getDateStr getListFileName getMd5Name utf8Encode xmlEscape getEncodingFromConfig);

use English;
use warnings;
use strict;
use Modern::Perl;
use Carp;
use Encode;
use XML::Simple;
use POSIX qw(strftime locale_h);

my $configFile = "conf.xml";

setlocale(LC_CTYPE, "ko_KR.utf8");
setlocale(LC_TIME, "C");

sub utf8Encode { return encode("utf-8", shift); }
sub utf8Decode { return decode("utf-8", shift); }


sub getMd5Name
{
	use Digest::MD5;
	return Digest::MD5::md5_hex(shift);
}


sub getDateStr
{
	my $ts = shift;
	return strftime("%Y%m%d", localtime($ts));
}


sub getListFileName
{
	my $listDir = shift;
	my $dateStr = shift;

	return $listDir . "/${dateStr}.txt";
}


sub xmlEscape
{
	my $str = shift;
	$str = utf8Decode($str);

	return "<![CDATA[" . $str . "]]>";
}


sub readConfig
{
	my $config = shift;

	my $xml = new XML::Simple;
	if (exists $ENV{'FEED_MAKER_CONF_FILE'}) {
		$configFile = $ENV{'FEED_MAKER_CONF_FILE'};
	}
	$$config = $xml->XMLin($configFile);
	if ($@) {
		confess "Error: can't read the configuration file, parse error!, "; 
		return -1;
	}
	return $$config;
}


sub getConfigValue
{
	my $config = shift;
	my $isCompulsory = shift;
	my $defaultValue = shift;
	my @configPath = @_;

	if (not defined $defaultValue) {
		$defaultValue = "";
	}

	if (defined $config) {
		my $c = $config;
		for my $name (@configPath) {
			$c = $c->{$name};
			if (not defined $c) {
				if ($isCompulsory == 1) {
					carp "Warning: can't find '$name' element from config\n";
					return $defaultValue;
				}
				return $defaultValue;
			}
		}
		return $c;
	}
	return $defaultValue;
}


sub printAllHashItems
{
	my $hash = shift;
	my $prefix = shift;

	foreach my $key (keys %$hash) {
		print "# " . $prefix . $key . " --> " . utf8Encode($hash->{$key}) . "\n";
	}
}


sub getEncodingFromConfig
{
	my $config = ();

	if (not FeedMaker::readConfig(\$config)) {
		confess "Error: can't read configuration!, ";
		return -1;
	}
	my $extraction_config = $config->{"extraction"};
	if (not defined $extraction_config) {
		confess "Error: can't read extraction config!, ";
		return -1;
	}
	my $encoding = $extraction_config->{"encoding"};
	if (not defined $encoding) {
		$encoding = "utf8";
	}

	return $encoding;
}


1
