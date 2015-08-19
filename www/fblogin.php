<!DOCTYPE html>
<html>
<head>
	<title>Facebook Login JavaScript Example</title>
	<meta charset="UTF-8">
 </head>
 <body>
<div id="status">
</div>

<a href="https://www.facebook.com/dialog/oauth?client_id=394515740746053&response_type=code&state=<?=time()?>&scope=email&redirect_uri=<?=urlencode("http://terzeron.net/fm/fblogin_check.php")?>">Login</a>

</body>
</html>
