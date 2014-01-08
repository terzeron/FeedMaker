<?php
error_reporting(E_ALL ^ E_NOTICE);

$work_dir = "./work";

function txt2html($content)
{
	$lines = explode("\n", $content);
	$div_open = 0;
	foreach ($lines as $line) {
		if (preg_match("/^\s*$/", $line) || $line == "Warning: can't get old list!") {
			continue;
		}
		$line = preg_replace("/</", "&lt;", $line);
		$line = preg_replace("/>/", "&gt;", $line);
		$line = preg_replace("/\033\[1;(\d+)m/", "<span class='c$1'>", $line);
		$line = preg_replace("/\033\[0(;0)?m/", "</span>", $line);
		$line = preg_replace("/^=====\s+([^=]+)\s+=====\s*$/", "<h4>$1</h4>", $line);
		$line = preg_replace("/^---\s+([^\-]+)\s+---\s*$/", "<h5>$1</h5>", $line);
		$line = preg_replace("/^==+$/", "<hr/>", $line);
		$line = preg_replace("/^\/(Users|home\d+).*\/(public_html(\/xml\/?)?)?/", "", $line);
		$starting_element = substr($line, 0, 4);
		if ($starting_element == "<h4>" || $starting_element == "<h5>") {
			// h4이나 h5등의 heading element로 시작하면
			if ($div_open == 1) {
				// 열려 있으면 일단 닫고
				print "</div>\n";
				$div_open = 0;
			}

			// 내용을 출력
			print "$line\n";

			// h5의 경우에 아래쪽 내용을 div로 감싸줘야 하므로 div를 열어 줌
			if ($starting_element == "<h5>") {
				print "<div class='block'>\n";
				$div_open = 1;
			}
		} else {
			print "$line\n";
		}
		if (!preg_match("/^<(h\d|div).*(h\d|div)>$/", $line)) {
			print "<br/>\n";
		}
	}
	if ($div_open == 1) {
		print "</div>\n";
	}
}
?>
