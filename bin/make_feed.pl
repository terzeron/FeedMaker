#!/usr/bin/env perl

use English;
use warnings;
use strict;
use Modern::Perl;
use Carp;
use Encode;
use Cwd;
use Getopt::Std;

use Digest::MD5;
use File::Path;
use XML::RSS;
use FeedMaker;
use POSIX qw(strftime);


local $OUTPUT_AUTOFLUSH = 1;
my $SECONDS_PER_DAY = 60 * 60 * 24;
my $MIN_CONTENT_LENGTH = 64;
my $MAX_CONTENT_LENGTH = 64 * 1024;
my $max_num_days = 3;


sub get_rss_date_str
{
	my $ts = shift;
	return strftime("%a, %d %b %Y %H:%M:%S %z", localtime($ts));
}


sub get_new_file_name
{
	my $url = shift;

	return "html/" . FeedMaker::getMd5Name($url) . ".html";
}


sub get_recent_list
{
	my $list_dir = shift;

	print "# get_recent_list($list_dir)\n";

	my $date_str = FeedMaker::getDateStr(time());
	my $newlist_file_name = FeedMaker::getListFileName($list_dir, $date_str);
	my $post_process_cmd = qq(| remove_duplicate_line.py > "$newlist_file_name");
	my $config = ();
	if (FeedMaker::readConfig(\$config)) {
		my $collection_config = $config->{"collection"};
		if ($collection_config) {
			my $post_process_script = FeedMaker::getConfigValue($config, 0, "", ("collection", "post_process_script"));
			if ($post_process_script) {
				$post_process_cmd = qq(| $post_process_script "$newlist_file_name");
			}
		}
	}

	my $cmd = qq(collect_new_list.pl ) . $post_process_cmd;
	print "# " . FeedMaker::utf8Encode($cmd) . "\n";
	my $result = qx($cmd);
	if ($CHILD_ERROR != 0) {
		confess "Error: can't collect new list from the page,";
		return;
	}
	print $result;

	if (not open(IN, $newlist_file_name)) {
		confess "Error: can't open file '$newlist_file_name' for reading, $ERRNO,";
		return -1;
	}
	my @uniq_list = ();
	while (my $line = <IN>) {
		chomp $line;
		push @uniq_list, $line;
	}
	close(IN);

	return @uniq_list;
}


sub read_old_list_from_file
{
	my $list_dir = shift;
	my $is_completed = shift;

	print "# read_old_list_from_file($list_dir, $is_completed)\n";

	my @list = ();
	my $ts = time();
	if ($is_completed == 0) {
		# 아직 진행 중인 피드에 대해서는 현재 날짜에 가장 가까운
		# 과거 리스트 파일 1개를 찾아서 그 안에 기록된 리스트를 꺼냄

		my $list_file = "";
		my $i = 0;
		# 과거까지 리스트가 존재하는지 확인
		for ($i = 1; $i <= $max_num_days; $i++) {
			my $date_str = FeedMaker::getDateStr($ts - $i * $SECONDS_PER_DAY);
			$list_file = FeedMaker::getListFileName($list_dir, $date_str);
			print "$list_file\n";
			# 오늘에 가장 가까운 리스트가 존재하면 탈출
			if (-e $list_file) {
				last;
			}
		}
		if ($i > $max_num_days) {
			return ();
		}
		# read the old list
		if (not open(IN, $list_file)) {
			confess "Error: can't open '$list_file' for reading, $ERRNO,";
			return -1;
		}
		while (my $line = <IN>) {
			chomp $line;
			push(@list, $line);
		}
		close(IN);
	} else {
		# 이미 완료된 피드에 대해서는 기존 리스트를 모두 취합함
		
		my %existence_check_map = ();
		opendir(my $dh, $list_dir);
		while (my $file_name = readdir($dh)) {
			if ($file_name eq "." or $file_name eq "..") {
				next;
			}
			if (not open(IN, $list_dir . "/" . $file_name)) {
				confess "Error: can't open '$file_name' for reading, $ERRNO,";
				return -1;
			}
			while (my $line = <IN>) {
				chomp $line;
				my ($url, $title) = split /\t/, $line;
				if (not exists $existence_check_map{$url}) {
					$existence_check_map{$url} = 1;
					push(@list, $line);
				}
			}
			close(IN);
		}
		closedir($dh);

	}

	return @list;
}


sub generate_rss_feed
{
	my $config = shift;
	my $arg = shift;	
	my @feed_list = @$arg;
	my $rss_file_name = shift;

	my $rss_config = $config->{"rss"};
	if (not defined $rss_config) {
		confess "Error: missing rss configuration\n";
		return -1;
	}
	my $rss_title = FeedMaker::utf8Encode(FeedMaker::getConfigValue($config, 1, "", ("rss", "title")));
	my $rss_description = FeedMaker::utf8Encode(FeedMaker::getConfigValue($config, 1, "", ("rss", "description")));
	my $rss_generator = FeedMaker::utf8Encode(FeedMaker::getConfigValue($config, 1, "", ("rss", "generator")));
	my $rss_copyright = FeedMaker::utf8Encode(FeedMaker::getConfigValue($config, 1, "", ("rss", "copyright")));
	my $rss_link = FeedMaker::utf8Encode(FeedMaker::getConfigValue($config, 1, "", ("rss", "link")));
	my $rss_language = FeedMaker::utf8Encode(FeedMaker::getConfigValue($config, 1, "", ("rss", "language")));
	my $rss_no_item_desc = FeedMaker::getConfigValue($config, 0, "", ("rss", "no_item_desc"));

	print "# generate_rss_feed($rss_file_name)\n";

	my $date_str = FeedMaker::getDateStr(time());
	my $pub_date_str = get_rss_date_str(time());
	my $last_build_date_str = get_rss_date_str(time());
	my $temp_rss_file_name = $rss_file_name . "." . $date_str;

	my $rss = XML::RSS->new(version => "2.0");
	$rss->channel(title => FeedMaker::xmlEscape($rss_title),
				  link => FeedMaker::xmlEscape($rss_link),
				  languauge => $rss_language,
				  description => FeedMaker::xmlEscape($rss_description),
				  copyright => FeedMaker::xmlEscape($rss_copyright),
				  pubDate => FeedMaker::xmlEscape($pub_date_str),
				  lastBuildDate => FeedMaker::xmlEscape($last_build_date_str),
				  generator => FeedMaker::xmlEscape($rss_generator),
			  );

	for my $feed_item (@feed_list) {
		my ($article_url, $article_title) = split /\t/, $feed_item;
		my $new_file_name = get_new_file_name($article_url);

		# notice!
		if (defined $rss_no_item_desc and $rss_no_item_desc =~ m!yes|true!) {
			# skip the content of the feed
			$rss->add_item(title => FeedMaker::xmlEscape($article_title),
						   link => FeedMaker::xmlEscape($article_url),
						   guid => FeedMaker::xmlEscape($article_url),
						   pubDate => FeedMaker::xmlEscape($pub_date_str));
		} else {
			# general case
			my $content = "";
			if (not open(IN, $new_file_name)) {
				# 영화토렌트의 경우 파일이 존재하지 않을 수도 있음
				#warn "Warning: can't open '$new_file_name' for reading, $ERRNO,";
				next;
			}
			print "adding '$new_file_name' to the result\n";
			while (my $line = <IN>) {
				$content .= $line;
				
				# restrict big contents
				if (length($content) >= $MAX_CONTENT_LENGTH) {
					$content = "<strong>본문이 너무 길어서 전문을 싣지 않았습니다. 다음의 원문 URL을 참고해주세요.</strong><br/>" . $content; 
					last;
				}
			}
			close(IN);
			$rss->add_item(title => FeedMaker::xmlEscape($article_title),
						   link => FeedMaker::xmlEscape($article_url),
						   guid => FeedMaker::xmlEscape($article_url),
						   pubDate => FeedMaker::xmlEscape($pub_date_str),
						   description => FeedMaker::xmlEscape($content));
		}
	}
	$rss->save($temp_rss_file_name);

	# 이번에 만들어진 rss 파일이 이전 파일과 내용이 다른지 확인
	my $is_different = 0;
	if (not -e $rss_file_name) {
		$is_different = 1;
	} else {
		my $cmd = qq(diff "$temp_rss_file_name" "$rss_file_name" | grep -v -Ee \"(^(<|>) <(pubDate|lastBuildDate))|(^---\$)|(^[0-9,]+[a-z][0-9,]+\$)\" | wc -c);
		print "$cmd\n";
		my $result = qx($cmd);
		print $result;
		chomp $result;
		if ($result =~ /^\s*(\d+)\s*$/ and $1 ne "0") {
			$is_different = 1;
		}
	}
	
	if ($is_different == 1) {
		# 이전 파일을 old 파일로 이름 바꾸기
		if (-e $rss_file_name) {
			my $cmd = qq(mv -f "$rss_file_name" "$rss_file_name.old");
			print "# $cmd\n";
			my $result = qx($cmd);
			if ($CHILD_ERROR != 0) {
				return -1;
			}
		}
		# 이번에 만들어진 파일을 정식 파일 이름으로 바꾸기
		if (-f $temp_rss_file_name) {
			my $cmd = qq(mv -f $temp_rss_file_name $rss_file_name);
			print "# $cmd\n";
			my $result = qx($cmd);
			if ($CHILD_ERROR != 0) {
				return -1;
			}
		}
	} else {
		# 이번에 만들어진 파일을 지우기
		my $cmd = qq(rm -f $temp_rss_file_name);
		print "# $cmd\n";
		my $result = qx($cmd);
		if ($CHILD_ERROR != 0) {
			return -1;
		}
	}

	return 0;
}


sub append_item_to_result
{
	my $feed_list_ref = shift;
	my $item = shift;
	my $rss_file_name = shift;

	my ($url, $title, $review_point) = split /\t/, $item;
	my $new_file_name = get_new_file_name($url);
	my $size = 0;
	if (-e $new_file_name and ($size = -s $new_file_name) >= $MIN_CONTENT_LENGTH) {
		# 이미 성공적으로 만들어져 있으니까 피드 리스트에 추가
		print "Success: $title: $url --> $new_file_name: $size\n";
		push(@$feed_list_ref, $item);
	} else {
		# 파일이 존재하지 않거나 크기가 작으니 다시 생성 시도
		#print "$title: $url --> $new_file_name: $size\n";
		my $cmd = "";

		my $post_process_cmd = "";
		my $config = ();
		if (not FeedMaker::readConfig(\$config)) {
			confess "Error: can't read configuration!, ";
			return -1;
		}
		my $extraction_config = $config->{"extraction"};
		if (not defined $extraction_config) {
		    confess "Error: missing extraction configuration\n";
			return -1;
		}

		my $post_process_script = FeedMaker::getConfigValue($config, 0, "", ("extraction", "post_process_script"));
		if ($post_process_script) {
			$post_process_cmd = qq(| $post_process_script "$url");
			my $post_process2_script = FeedMaker::getConfigValue($config, 0, "", ("extraction", "post_process2_script"));
			if ($post_process2_script) {
				$post_process_cmd .= qq( | $post_process2_script "$url");
			}
		}
		
		my $render_js = FeedMaker::getConfigValue($config, 0, 0, ("extraction", "render_js"));
		my $option = "";
		if (defined $render_js and $render_js =~ m!yes|true!i) {
			$option = "--render-js";
		}
		my $force_sleep_between_articles = FeedMaker::getConfigValue($config, 0, 0, ("extraction", "force_sleep_between_articles"));
		my $bypass_element_extraction = FeedMaker::getConfigValue($config, 0, 0, ("extraction", "bypass_element_extraction"));
		my $review_point_threshold = FeedMaker::getConfigValue($config, 0, "", ("extraction", "review_point_threshold"));
	
		#print "title=$title, review_point=$review_point, review_point_threshold=$review_point_threshold\n";
		if (defined $review_point and $review_point ne "" and 
			defined $review_point_threshold and $review_point_threshold ne "" and 
			$review_point > $review_point_threshold) {
			# 일반적으로 평점이 사용되지 않는 경우나
			# 평점이 기준치를 초과하는 경우에만 추출
			warn "Warning: ignore an article due to the low score\n";
			return 0;
		}

		my $extraction_cmd = qq(| extract.py "$url");
		if ($bypass_element_extraction =~ m!yes|true!) {
			$extraction_cmd = "";
		}

		$cmd = qq(wget.sh $option "$url" $extraction_cmd $post_process_cmd > "$new_file_name");
		print "# $cmd\n";
		my $result = qx($cmd);
		if ($CHILD_ERROR != 0) {
			confess "Error: can't extract HTML elements,";
			return -1;
		}
		my $md5_name = FeedMaker::getMd5Name($url);
		$size = -s $new_file_name;
		if ($size > 0) {
			$cmd = qq(echo "<img src='http://terzeron.net/img/1x1.jpg?feed=${rss_file_name}&item=${md5_name}'/>" >> "${new_file_name}");
			print "# $cmd\n";
			$result = qx($cmd);
			if ($CHILD_ERROR != 0) {
				confess "Error: can't append page view logging tag,";
				return -1;
			}
		}
		$size = -s $new_file_name;
		if ($size < $MIN_CONTENT_LENGTH) {
			# 피드 리스트에서 제외
			warn "Warning: $title: $url --> $new_file_name: $size (< $MIN_CONTENT_LENGTH byte)\n";
			return 0;
		} else {
			# 피드 리스트에 추가
			print "Success: $title: $url --> $new_file_name: $size\n";
			push(@$feed_list_ref, $item);
		}

		if ($force_sleep_between_articles =~ m!yes|true!i) {
			sleep(1);
		}
	}
}


sub diff_old_and_recent
{
	my $arg = shift;
	my @recent_list = @$arg;
	$arg = shift;
	my @old_list = @$arg;
	my $feed_list_ref = shift;
	my $rss_file_name = shift;

	my %old_map = ();

	print "# diff_old_and_recent($rss_file_name)\n";

	for my $old (@old_list) {
		if ($old =~ /^\#/) {
			next;
		}
		my ($url, $title) = split /\t/, $old;
		$old_map{$url} = $title;
	}
	#print scalar(@old_list) . "\n";

	# differentiate
	my @result_list = ();
	for my $recent (@recent_list) {
		if ($recent =~ /^\#/) {
			next;
		}
		my ($url, $title) = split /\t/, $recent;
		if (not exists($old_map{$url})) {
			push(@result_list, $recent);
			print "not exists $recent\n";
		} else {
			print "exists $recent\n";
		}
	}

	# collect items to be generated as RSS feed
	print "Appending " . scalar(@result_list) . " new item to the feed list\n";
	for my $new_item (reverse @result_list) {
		if ($new_item =~ /^\#/) {
			next;
		}
		append_item_to_result($feed_list_ref, $new_item, $rss_file_name);
	}
	print "Appending " . scalar(@old_list) . " old item to the feed list\n";
	for my $old_item (reverse @old_list) {
		if ($old_item =~ /^\#/) {
			next;
		}
		append_item_to_result($feed_list_ref, $old_item, $rss_file_name);
	}

	if (scalar @$feed_list_ref == 0) {
		print "Notice: 새로 추가된 feed가 없으므로 결과 파일을 변경하지 않음\n";
		return -1;
	}

}


sub get_start_idx
{
	my $file_name = shift;

	print "# get_start_idx($file_name)\n";

	if (not open(IN, $file_name)) {
		write_next_start_idx($file_name, 0);
		return (0, int(time));
	}
	my $line = <IN>;
	my $start_idx = 0;
	my $mtime = 0;
	if ($line =~ m!(\d+)\t(\d+)!) {
		$start_idx = $1;
		$mtime = $2;
	}
	close(IN);

	print "start index: $start_idx\n";
	print "last modified time: $mtime, " . localtime($mtime) . "\n";

	return (int($start_idx), $mtime);
}


sub write_next_start_idx
{
	my $file_name = shift;
	my $next_start_idx = shift;

	print "# write_next_start_idx($file_name, $next_start_idx)\n";
	
	open(OUT, "> $file_name");
	print "next start index: " . int($next_start_idx) . "\n";
	print "current time: " . int(time) . ", " . localtime(time) . "\n";
	print OUT int($next_start_idx) . "\t" . int(time) . "\n";
	close(OUT);
}


sub print_usage
{
	print "usage:\t$PROGRAM_NAME\t<config file> <rss file>\n";
	print "\n";
}


sub cmp_int_or_str
{
	if ($a->{"sf"} =~ m!^\d+$! and $b->{"sf"} =~ m!^\d+$!) { 
		return (int($a->{"sf"}) <=> int($b->{"sf"}));
	} else { 
		return ($a->{"sf"} <=> $b->{"sf"});
	}
}


sub main
{
	print STDOUT "=========================================================\n";
	print STDOUT " " . getcwd() . " \n";
	print STDOUT "=========================================================\n";

	my $force_collect = 0;
	my %opts = ();
	my $opt_str = "c";
	our $opt_c;
	getopts($opt_str, \%opts);
	if (defined $opts{"c"}) {
		$force_collect = 1;
	}

	if (scalar @ARGV < 1) {
		print_usage();
		return -1;
	}

	my $rss_file_name = $ARGV[0];

	# from configuration
	my $config = ();
	if (not FeedMaker::readConfig(\$config)) {
		confess "Error: can't read configuration!,";
	}

	my $ignore_old_list = FeedMaker::getConfigValue($config, 0, 0, ("collection", "ignore_old_list"));
	if (defined $ignore_old_list and $ignore_old_list =~ m!yes|true!i) {
		$ignore_old_list = 1;
	} else {
		$ignore_old_list = 0;
	}
	#print "ignore_old_list:" . $ignore_old_list . "\n";

	my $is_completed = FeedMaker::getConfigValue($config, 0, "", ("collection", "is_completed"));
	if (not defined $is_completed or $is_completed eq "") {
		$is_completed = 0;
	} else {
		print "# is_completed: $is_completed\n";
		if ($is_completed =~ m!yes|true!i) {
			$is_completed = 1;
		} elsif ($is_completed =~ m!(no|false)!i) {
			$is_completed = 0;
		} else {
			confess "Error: can't identify boolean type '$is_completed'\n";
			return -1;
		}
	}
	# -c 옵션이 지정된 경우, 설정의 is_completed 값 무시
	if ($force_collect == 1) {
		$is_completed = 0;
	}

	my $list_dir = "newlist";
	mkpath($list_dir);
	mkpath("html");

    # 과거 피드항목 리스트를 가져옴
	my @feed_list = ();
	my @old_list = read_old_list_from_file($list_dir, $is_completed);
	if (not @old_list) {
		warn "Warning: can't get old list!\n";
	}

	# 완결여부 설정값 판단 
	my @recent_list = ();
	if ($is_completed == 1) {
		# 완결된 피드는 적재된 리스트에서 일부 피드항목을 꺼내옴

		# 오름차순 정렬
		# fnn: 타이틀의 \[\d+\] 패턴
		# naver: no 파라미터 값 또는 타이틀의 \d+\. 패턴
		# daum: url 마지막 값
		# stoo: id 파라미터 값 문자열사전순 비교
		# nate: bsno 파라미터 값 또는 타이틀의 \d+회 패턴
		# hani: url 마지막 값
		# moneytoday: nViewSeq 파라미터 값
		my @feed_id_sf_list = ();
		my %feed_item_existence_map = ();
		my $sort_field_pattern = FeedMaker::getConfigValue($config, 1, "", ("collection", "sort_field_pattern"));
		my $unit_size_per_day = FeedMaker::getConfigValue($config, 1, "", ("collection", "unit_size_per_day"));

		for (my $i = 0; $i < scalar @old_list; $i++) {
			my $sf = "";
			if ($old_list[$i] =~ qr/$sort_field_pattern/o) {
				$sf = $1;
			} else {
				warn "Warning: can't match the pattern /$sort_field_pattern/\n";
			}
			if (not exists $feed_item_existence_map{$old_list[$i]}) {
				my %feed_id_sf = ("id" => $i, "sf" => $sf);
				$feed_item_existence_map{$old_list[$i]} = 1;
				push @feed_id_sf_list, \%feed_id_sf;
			}
		}
		my @sorted = sort cmp_int_or_str @feed_id_sf_list;
		my $i = 0;
		my $idx_file = "start_idx.txt";
		my $window_size = 10; # feedly initial max window size
		my ($start_idx, $mtime) = get_start_idx($idx_file);
		my $end_idx = $start_idx + $window_size;
		for my $feed (@sorted) {
			if ($i >= $start_idx and $i < $end_idx) {
				push @feed_list, $old_list[$feed->{"id"}];
				print $old_list[$feed->{"id"}] . "\n";
			}
			$i++;
		}
		my $increment_size = int((int(time) - $mtime) * int($unit_size_per_day) / 86400);
		print "# start_idx=$start_idx, end_idx=$end_idx, current time=" . int(time) . ", mtime=$mtime, window_size=$window_size, increment_size=$increment_size\n";
		if ($increment_size > 0) {
			write_next_start_idx($idx_file, $start_idx + $increment_size);
		}
	} else {
		# 피딩 중인 피드는 최신 피드항목을 받아옴
		@recent_list = get_recent_list($list_dir);
		if (not @recent_list) {
			confess "Error: can't get recent list!,";
		}
		
		# 과거 피드항목 리스트와 최근 피드항목 리스트를 비교함
		if ($ignore_old_list == 1) {
			@old_list = ();
			@feed_list = @recent_list;
		}
		if (diff_old_and_recent(\@recent_list, \@old_list, \@feed_list, $rss_file_name) < 0) {
			return -1;
		}
	}

	if ($force_collect == 0) {
		# generate RSS feed
		if (generate_rss_feed($config, \@feed_list, $rss_file_name) < 0) {
			return -1;
		}
	}
	
	# upload RSS feed file
	my $cmd = qq(upload.py $rss_file_name);
	print "# $cmd\n";
	my $result = qx($cmd);
	print $result;
	if ($CHILD_ERROR != 0) {
		return -1;
	}

	if ($result =~ m!Upload: success! and $force_collect == 0) {
		# email notification
		my $email = FeedMaker::getConfigValue($config, 0, "", ("notification", "email"));
		if (defined $email and $email ne "") {
			my $recipient = FeedMaker::getConfigValue($config, 1, "", ("notification", "email", "recipient"));
			my $subject = FeedMaker::getConfigValue($config, 1, "", ("notification", "email", "subject"));
			open(OUT, "| mail -s '$subject' '$recipient'");
			for my $feed (@recent_list) {
				print OUT $feed . "\n";
			}
			close(OUT);
			print "sent a notification in mail\n";
		} 		
	}
	
	return 0;
}


exit main();
