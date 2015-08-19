<?php
echo "GET<br>\n";
var_dump($_GET);
echo "<br>\n";

$app_id = "394515740746053";
$redirect_uri = urlencode("http://terzeron.net/fm/fblogin_check.php");
$secret = "8f3ba60272204bdd950c769f9fe5992b";
$code = $_GET["code"];
/*
$response = http_get("https://graph.facebook.com/v2.3/oauth/access_token?client_id=<?=$app_id?>&redirect_uri=<?=urlencode($redirect_uri)?>&client_secret=<?=$secret?>&code=<?=$code?>");
echo "reponse=$reponse<br>\n";
var_dump($response);
*/
$c = fopen("https://graph.facebook.com/v2.3/oauth/access_token?client_id=$app_id&client_secret=$secret&code=$code&redirect_uri=$redirect_uri", "r");
$response = fread($c);
echo "response=$response<br>\n";
var_dump($response);
fclose($c);
?>
