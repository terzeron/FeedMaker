#!/usr/bin/env perl

package FeedMaker;

use base 'Exporter';
our @EXPORT = qw(read_config get_config_value print_items print_all_hash_items get_date_str get_list_file_name get_md5_name utf8_decode utf8_encode xml_escape get_encoding_from_config);

use English;
use warnings;
use strict;
use Modern::Perl;
use Carp;
use Encode;
use XML::Simple;
use POSIX qw(strftime locale_h);

my $config_file = "conf.xml";

setlocale(LC_CTYPE, "ko_KR.utf8");
setlocale(LC_TIME, "C");

sub utf8_encode { return encode("utf-8", shift); }
sub utf8_decode { return decode("utf-8", shift); }
sub cp949_decode { return decode("cp949", shift); }


sub get_md5_name
{
	use Digest::MD5;
	return Digest::MD5::md5_hex(shift);
}


sub get_date_str
{
	my $ts = shift;
	return strftime("%Y%m%d", localtime($ts));
}


sub get_list_file_name
{
	my $list_dir = shift;
	my $date_str = shift;

	return $list_dir . "/${date_str}.txt";
}


sub xml_escape
{
	my $str = shift;
	$str = utf8_decode($str);

	return "<![CDATA[" . $str . "]]>";
}


sub read_config
{
	my $config = shift;

	my $xml = new XML::Simple;
	if (exists $ENV{'FEED_MAKER_CONF_FILE'}) {
		$config_file = $ENV{'FEED_MAKER_CONF_FILE'};
	}
	$$config = $xml->XMLin($config_file);
	if ($@) {
		confess "Error: can't read the configuration file, parse error!, "; 
		return -1;
	}
	return $$config;
}


sub get_config_value
{
	my $config = shift;
	my $is_compulsory = shift;
	my $default_value = shift;
	my @config_path = @_;

	if (not defined $default_value) {
		$default_value = "";
	}

	if (defined $config) {
		my $c = $config;
		for my $name (@config_path) {
			$c = $c->{$name};
			if (not defined $c) {
				if ($is_compulsory == 1) {
					carp "Warning: can't find '$name' element from config\n";
					return $default_value;
				}
				return $default_value;
			}
		}
		return $c;
	}
	return $default_value;
}


sub print_items
{
	my $value = shift;
	my $prefix = shift;

	if (UNIVERSAL::isa($value, 'ARRAY')) {
		foreach my $item (@$value) {
			print "# " . $prefix . $item . "\n";
		}
	} elsif (UNIVERSAL::isa($value, 'HASH')) {
		foreach my $key (keys %$value) {
			print "# " . $prefix . $key . " --> " . utf8_encode($value->{$key}) . "\n";
		}
	} elsif ($value ne "") {
		print "# " . $prefix . $value . "\n";
	}
}


sub print_all_hash_items
{
	my $hash = shift;
	my $prefix = shift;

	foreach my $key (keys %$hash) {
		print "# " . $prefix . $key . " --> " . utf8_encode($hash->{$key}) . "\n";
	}
}


sub print_all_array_items
{
	my $arr = shift;
	my $prefix = shift;

	foreach my $item (@$arr) {
		print "# " . $prefix . $item . "\n";
	}
}


sub get_user_input
{
	my $question = shift;

	print $question;
	my $answer = <>;
	chomp $answer;
	return $answer
}


sub get_encoding_from_config
{
	my $config = ();

	if (not FeedMaker::read_config(\$config)) {
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
