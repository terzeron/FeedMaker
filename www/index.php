<?header("Cache-Control: no-cache, must-revalidate");?>
<!DOCTYPE HTML>
<html>
  <head>
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
	<meta name="viewport" content="width=device-width" />
	<meta name="viewport" content="initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0" />
	<script src="jquery-ui-1.10.3/jquery-1.9.1.js"></script>
	<script src="jquery-ui-1.10.3/ui/minified/jquery-ui.min.js"></script>
	<!--script src="jquery-ui-1.10.3/ui/minified/jquery.ui.tabs.min.js"></script-->
	<!--link rel="stylesheet" href="jquery-ui-1.10.3/demos/demos.css" /-->
	<link rel="stylesheet" href="jquery-ui-1.10.3/themes/base/minified/jquery-ui.min.css" />
	<link rel="stylesheet" href="style.css"/>
	<title>FeedMaker 관리</title>
  </head>
  <body>
	<script>
     $(function() {
       $( "#tabs" ).tabs();
	 });
	</script>
	<div id="tabs">
	  <ul>
		<li><a href="#tabs-1">실행 결과</a></li>
		<li><a href="#tabs-2">문제점 조회</a></li>
		<li><a href="#tabs-3">피드 관리</a></li>
	  </ul>
	  <div id="tabs-1">
		<p>
		  <?include("show_log.php");?>
		</p>
	  </div>
	  <div id="tabs-2">
		<p>
		  <?include("find_problems.php");?>
		</p>
	  </div>
	  <div id="tabs-3">
		<p>
		  <?include("add_feed.php");?>
		</p>
	  </div>
	</div>
  </body>
</html>
