#!/usr/bin/env perl

use English;
use strict;
use warnings;
use Carp;
use Encode;

use HTML::Parser;
use FeedMaker;


# multiline matching
$/ = "";


sub extract_urls
{
	my $render_js = shift;
	my $url = shift;
	my $item_capture_script = shift;
	my $user_agent = shift;
    my $referer = shift;
	#print "# extract_urls($url, $item_capture_script, $user_agent, $referer)\n";

	my $option = "";
	if ($render_js == 1) {
		$option = "--render-js";
	}
	if ($user_agent ne "") {
		$option .= " --ua '$user_agent'";
	}
    if ($referer ne "") {
        $option = "--referer '$referer'";
    }
	my $cmd = qq(wget.sh $option "$url" | extract_element.py collection | $item_capture_script);
	print "# $cmd\n";
	my $result = `$cmd`;
	if ($CHILD_ERROR != 0) {
		confess "Error: can't execute '$cmd', $ERRNO\n";
		return;
	}

	my @result_list = split /\n/, $result;
	# check the result
	foreach my $item (@result_list) {
		if ($item =~ /^\#/) {
			next;
		}
		my @tuple = split /\t/, $item;
		if (scalar @tuple < 2 or $tuple[0] eq "" or $tuple[1] eq "") {
			confess "Error: can't get the link and title from '$item',";
			return;
		}
	}
	return @result_list;
}


sub compose_url_list
{
	my $render_js = shift;
	my $list_url_list = shift ;
	my $item_capture_script = shift;
	my $user_agent = shift;
    my $referer = shift;
	my $total_list = shift;

	if (not defined $list_url_list) {
		$list_url_list = "";
	} 

	print "# compose_url_list($render_js, $list_url_list, $item_capture_script, $referer, $total_list)\n";

	foreach my $key (keys %$list_url_list) {
		my $value = $list_url_list->{$key};
		if (UNIVERSAL::isa($value, 'ARRAY')) {
			# list_url_list 아래 list_url이 여러 개 존재하는 경우
			foreach my $url (@$value) {
				my $a_url = $url;
				my @url_list = extract_urls($render_js, $a_url, $item_capture_script, $user_agent, $referer);
				push @$total_list, @url_list;
			}
		} else {
            # list_url_list 아래 list_url이 하나 존재하는 경우
			my $a_url = $value;
			my @url_list = extract_urls($render_js, $a_url, $item_capture_script, $user_agent, $referer);
			push @$total_list, @url_list;
		}
	}
}


sub main
{
	#print "# main()\n";

	my @total_list = ();

	# configuration
	my $config = ();
	if (not readConfig(\$config)) {
		confess "Error: can't read configuration!,";
		return -1;
	}

	my $render_js = FeedMaker::getConfigValue($config, 0, 0, ("collection", "render_js"));
	if (defined $render_js and $render_js =~ m!(true|yes)!i) {
		$render_js = 1;
	} else {
		$render_js = 0;
	}

	my $list_url_list = $config->{"collection"}->{"list_url_list"};
	if (defined $list_url_list) {
		print "# list_url_list:\n";
		FeedMaker::printAllHashItems($list_url_list, "  - ");
	}

	my $item_capture_script = FeedMaker::getConfigValue($config, 0, "", ("collection", "item_capture_script"));
	if (not defined $item_capture_script or $item_capture_script eq "") {
		$item_capture_script = "./capture_item_link_title.pl";
        if (not -e $item_capture_script) {
            $item_capture_script = "./capture_item_link_title.py";
        }
	}
	print "# item_capture_script: $item_capture_script\n";
	my ($item_capture_script_program,) = split /\s+/, $item_capture_script;
	if ($item_capture_script_program and not -x $item_capture_script_program) {
		confess "Error: can't execute '$item_capture_script_program',";
		return -1;
	}

	my $user_agent = FeedMaker::getConfigValue($config, 0, "", ("collection", "user_agent"));

    my $referer = FeedMaker::getConfigValue($config, 0, "", ("collection", "referer"));

	# collect items from specified url list
	print "# collecting items from specified url list...\n";
	compose_url_list($render_js, $list_url_list, $item_capture_script, $user_agent, $referer, \@total_list);

	foreach my $item (@total_list) {
		print $item . "\n";
	}

	return 0;
}


main();
