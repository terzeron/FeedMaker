<div>
  <?php
  require_once("common.inc");
  $content = file_get_contents("$work_dir/log/all.log");
  txt2html($content);
  ?>
</div>
