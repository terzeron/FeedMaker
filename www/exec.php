<?php
header("Cache-Control: no-cache; must-revalidate;");

require_once("common.inc");

$message = "";
$dir = "xmls";


function get_feed_list($parent_name)
{
	global $work_dir, $dir, $message;

	$feed_list = array("피드선택");
	$dir = $work_dir . "/" . $parent_name;
	if (is_dir($dir)) {
		if ($dh = opendir($dir)) {
			while (($fd_dir = readdir($dh))) {
				if (file_exists($dir . "/" . $fd_dir . "/conf.xml")) {
					array_push($feed_list, $fd_dir);
				}
			}
		}
	}

	$message = $feed_list;
	return 0;
}


function get_feed_content($parent_name,  $sample_feed)
{
	global $work_dir, $dir, $message;

	$filepath = $work_dir . "/" . $parent_name . "/" . $sample_feed . "/conf.xml";  
	$xml_text = "";                                                           
	if (file_exists($filepath)) {
		$fp = fopen($filepath, "r");                                                
		while (!feof($fp)) {                                                      
			$line = fread($fp, 4096);                                               
			$xml_text .= $line;
		}
		fclose($fp);
	} else {
		$message = "can't find such a feed, ${filepath}";
		return -1;
	}

	$message = $xml_text;
	return 0;
}


function save($parent_name, $feed_name)
{
	global $work_dir, $dir, $message;

	$filepath = $work_dir . "/" . $parent_name . "/" . $feed_name . "/conf.xml";
	if (file_exists($filepath)) {
		$message = "can't overwrite the existing file";
		return -1;
	}

	// save
	$text = $_POST["xml_text"];
	$fp = fopen("$dir/${feed_name}.xml", "w");
	if (!$fp) {
		$message = "can't open file '$feed_name.xml' for writing";
		return -1;
	}
	$result = fwrite($fp, $text, 4096);	
	if ($result == false) {
		$message = "can't write data to file";
		return -1;
	}
	fclose($fp);
	
	return 0;
}


function lint($feed_name)
{
	global $dir, $message;

	// lint
	$cmd = "/usr/bin/xmllint --noout $dir/${feed_name}.xml";
	$result = system($cmd);
	if ($result != "") {
		$message = "can't execute lint command";
		return -1;
	}

	return 0;
}


function extract_data($parent_name, $feed_name)
{
	global $work_dir, $dir, $message;

	$cmd = "\
mkdir ${work_dir}/${parent_name}/${feed_name}; \
cd ${work_dir}/${parent_name}/${feed_name}; \
mv ../../www/xmls/${feed_name}.xml conf.xml; \
. ../../bin/setup.sh; \
../../bin/run.sh > run.log 2> error.log; \
";
	$result = shell_exec($cmd);
	if (preg_match("/Error:/", $result)) {
		$message = "can't execute extract command, $result";
		return -1;
	}
	
	return 0;
}


function setacl($parent_name, $feed_name, $sample_feed)
{
	global $dir, $message;

	//date_default_timezone_set("Asia/Seoul");
	
	$timestamp = strftime("%y%m%d%H%M%S");
	$cmd = "cp /Users/terzeron/public_html/.htaccess /Users/terzeron/public_html/.htaccess.$timestamp";
	$ret = shell_exec($cmd);
	$infile = "/Users/terzeron/public_htm/.htaccess";
	$outfile = $infile . ".temp." . $timestamp;

	$infp = fopen($infile, "r");
	if (!$infp) {
		$message = "can't open file '$infile' for reading, $ret";
		return -1;
	}
	$outfp = fopen($outfile, "w");
	if (!$outfp) {
		$message = "can't open file '$infile' for writing, $ret";
		return -1;
	}
	while (!feof($infp)) {
		$content = fgets($infp);
		if (preg_match("/${sample_feed}\\\.xml/", $content)) {
			fputs($outfp, "RewriteRule\t^$feed_name\\.xml\$\txml/$feed_name\\.xml\n");
		}
		fputs($outfp, $content);
	}
	fclose($outfp);
	fclose($infp);

	if (!rename($outfile, $infile)) {
		$message = "can't rename file '$infile' to '$outfile'";
		return -1;
	}
	
	return 0;
}


function remove($parent_name, $sample_feed)
{
	global $work_dir, $dir, $message;

	// 
	// ACL 설정 제거
	//

	$timestamp = strftime("%y%m%d%H%M%S");
	$cmd = "cp /Users/terzeron/public_html/.htaccess /Users/terzeron/public_html/.htaccess.$timestamp";
	$ret = shell_exec($cmd);
	$infile = "/Users/terzeron/public_html/.htaccess";
	$outfile = $infile.".temp.".$timestamp;

	$infp = fopen($infile,"r");
	if (!$infp) {
		$message = "can't open file '$infile' for reading, $ret";
		return -1;
	}
	$outfp = fopen($outfile, "w");
	if (!$outfp) {
		$message = "can't open file '$infile' for writing, $ret";
		return -1;
	}
	while (!feof($infp)) {
		$content = fgets($infp);
		if (preg_match("/${sample_feed}\\\.xml/", $content)) {
			continue;
		}
		fputs($outfp, $content);
	}
	fputs($outfp, "RewriteRule\t^(xml/)?${sample_feed}\\.xml\$\t- [G]\n");
	fclose($outfp);
	fclose($infp);

	if (!rename($outfile, $infile)) {
		$message = "can't rename file '$infile' to '$outfile'";
		return -1;
	}
	
	//
	// 피드 디렉토리 정리
	//
	$cmd = "\
rm -f ../xml/${sample_feed}.xml; \
cd ${work_dir}/${parent_name}/${sample_feed}; \
rm -rf html newlist run.log error.log ${sample_feed}.xml ${sample_feed}.xml.old start_idx.txt; \
mv conf.xml conf.xml.old\
";
	$result = system($cmd);
	if ($result != "") { 
		$message = "can't clean the feed directory, $result";
		return -1;
	}
	
	return 0;
}


function exec_command()
{
	global $message, $dir;
	
	if ($_SERVER["REQUEST_METHOD"] != "POST"){
		$message = "can't accept method '" . $_SERVER["REQUEST_METHOD"] . "'";
		return -1;
	}
	$feed_name = $_POST["feed_name"];
	if (!preg_match("/^\w*$/", $feed_name)){
		$message = "The feed name must be only alphanumeric word.";
		return -1;
	}
	$parent_name = $_POST["parent_name"];
	if (!preg_match("/^\w*$/", $parent_name)){
		$message = "The parent name must be only alphanumeric word.";
		return -1;
	}
	$sample_feed = $_POST["sample_feed"];
	if (!preg_match("/^\w*$/", $sample_feed)){
		$message = "The sample feed name must be only alphanumeric word.";
		return -1;
	}
	$command = $_POST["command"];
	if ($command == "get_feed_list"){
		return get_feed_list($parent_name);
	} else if ($command == "get_feed_content"){
		return get_feed_content($parent_name, $sample_feed);
	} else if ($command == "save"){
		return save($parent_name, $feed_name);
	} else if ($command == "lint"){
		return lint($feed_name);
	} else if ($command == "extract"){
		return extract_data($parent_name, $feed_name);
	} else if ($command == "setacl"){
		return setacl($parent_name, $feed_name, $sample_feed);
	} else if ($command == "remove"){
		return remove($parent_name, $sample_feed);
	} else {
		$message = "can'tidentifythecommand";
		return -1;
	}
	
	return0;
}


$result = exec_command();
?>
{ "result" : "<?=$result?>", "message" : <?=json_encode($message)?> }
