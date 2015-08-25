<div>
	<?php
	require_once("common.inc");
	$content = file_get_contents("$work_dir/log/find_problems.log");
	txt2html($content);
	?>
</div>
