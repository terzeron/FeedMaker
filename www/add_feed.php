<?php
require_once("common.inc");

$feed_dir = $_GET{"feed_dir"};

// get category list
$category_list = array("카테고리선택");
if (is_dir($work_dir)) {
	if ($dh = opendir($work_dir)) {
		while (($dir = readdir($dh))) {
			if (!preg_match("/(\.|\.\.|bin|log|test)/", $dir) && $dir[0] != "_" && is_dir($work_dir . "/" . $dir)) {
				array_push($category_list, $dir);
			}
		}
	}
}
?>

<h4>Feed 추가</h4>

<div class="block">
	<div>
		카테고리: <select id="dir_list" name="category_dir">
		<?foreach ($category_list as $k) {?>
			<option name="<?=$k?>" value="<?=$k?>"><?=$k?></option>
		<?}?>
		</select>
		&nbsp;
		샘플 피드: <select id="feed_list" name="feed_dir">
		</select>
	</div>

	<div id="xml">
	</div>

	<div>
		<div>새로운 Feed 이름: <input type='text' id='feed_name' name='feed_name'/>.xml에 <input type='button' id='save' value='저장'/></div>
		<span>
			<input type='button' id='lint' value='XML lint 실행'/>
			<input type='button' id='extract' value='추출 실행'/>
			<input type='button' id='setacl' value='ACL 설정'/>
			<input type='button' id='disable' value='비활성화'/>
			<input type='button' id='remove' value='삭제'/>
			<input type='button' id='reset' value='초기화'/>
		</span>
		<div id='status'></div>
	</div>
    <div>
		<a id='feedly_link' href='#' target='_blank' style='display: none;'>Feedly에 등록</a>
    </div>
</div>

<script type="text/javascript">
 var ajax_url = "exec.php";
 
 function check_feed_name(feed_name) {
	 if (feed_name == undefined || feed_name == "") {
		 alert("Feed 이름을 입력하세요." + "feed_name='" + feed_name + "'");
		 return -1;
	 }
	 return 0;
 }
 
 function get_error_message(str) {
	 return "<span style='color:red;'>" + str + "</span>";
 }
 
 function get_success_message(str) {
	 return "<span style='color:green;'>" + str + "</span>";
 }
 
 // dir_list selectbox event handler
 $("#dir_list").change(function() {
	 $("#dir_list option:selected").each(function() {
		 var parent_name = $(this).val();
		 $.post(
			 ajax_url,
			 { "command": "get_feed_list", "parent_name": parent_name },
			 function(data, textStatus, jqXHR) {
				 res = jQuery.parseJSON(data);
				 if (res["result"] != "0") {
					 alert("can't get feed list");
				 } else {
					 html = "";
					 for (var i = 0; i < res["message"].length; i++) {
						 html += '<option value="' + res["message"][i] + '">' + res["message"][i] + '</option>'; 
					 }
					 $("#feed_list").html(html);
				 }
			 }
		 );
	 });
	 resetHandler();
 });

 $("#feed_list").change(function() {
	 $("#feed_list option:selected").each(function() {
         var parent_name = $("#dir_list").val();
         var sample_feed = $(this).val();
		 $.post(
			 ajax_url,
			 { "command": "get_feed_content", "sample_feed": $(this).val(), "parent_name": $("#dir_list").val() },
			 function(data, textStatus, jqXHR) {
				 res = jQuery.parseJSON(data);
				 if (res["result"] != "0") {
					 alert("can't get feed content");
				 } else {
					 html = res["message"];
					 new_html = html;
					 new_html = new_html.replace(/</g, "&lt;")
										.replace(/>/g, "&gt;<br/>")
									 .replace(/\t/g, "&nbsp;&nbsp;&nbsp;&nbsp;")
									 .replace(/&lt;!\[CDATA\[(.*)\]\]&gt;/g, "&lt;![CDATA[<input class='cdata' type='text' value=\"\$1\" size='80'/>]]&gt;");
					 $("#xml").html(new_html);
				 }
			 }
		 );
	 });
	 resetHandler();
 });
 
 // save button event handler
 var saveHandler = function() {
	 $("#save").val("저장 중");
	 var feed_name = $("#feed_name").val();
	 var parent_name = $("#dir_list").val();
	 var sample_feed = $("#feed_list option:selected").val();
	 if (check_feed_name(feed_name) < 0) {
		 return -1;
	 }
	 var cdata_arr = read_form_cdata();
	 var xml_text = replace_form_with_cdata(cdata_arr);
	 $.post(
		 ajax_url,
		 { "command": "save", "feed_name": feed_name, "parent_name": parent_name, "sample_feed": sample_feed, "xml_text": xml_text },
		 function(data, textStatus, jqXHR) {
			 res = jQuery.parseJSON(data);
			 if (res["result"] != "0") {
				 $("#status").html(get_error_message(res["message"]));
			 } else {
				 $("#status").html(get_success_message(feed_name + ".xml 파일이 저장되었습니다."));
				 $("#save").val("저장 완료");
				 $("#save").button({disabled: true});
			 }
		 }
	 );
 };
 
 // lint button event handler
 var lintHandler = function() {
	 $("#lint").val("XML lint 실행 중");
	 var feed_name = $("#feed_name").val();
	 var parent_name = $("#dir_list").val();
	 var sample_feed = $("#feed_list option:selected").val();
	 $.post(
		 ajax_url,
		 { "command": "lint", "feed_name": feed_name, "parent_name": parent_name, "sample_feed": sample_feed },
		 function(data, textStatus, jqXHR) {
			 res = jQuery.parseJSON(data);
			 if (res["result"] != "0") {
				 $("#status").html(get_error_message(res["message"]));
			 } else {
				 $("#status").html(get_success_message("XML 검사 완료"));
				 $("#lint").val("XML lint 실행 완료");
				 $("#lint").button({disabled: true});
			 }
		 }
	 );
 };	 

 // extract button event handler
 var extractHandler = function() {
	 $("#extract").val("추출 실행 중");
	 var feed_name = $("#feed_name").val();
	 var parent_name = $("#dir_list").val();
	 var sample_feed = $("#feed_list option:selected").val();
	 $.post(
		 ajax_url,
		 { "command": "extract", "feed_name": feed_name, "parent_name": parent_name, "sample_feed": sample_feed },
		 function(data, textStatus, jqXHR) {
			 res = jQuery.parseJSON(data);
			 if (res["result"] != "0") {
				 $("#status").html(get_error_message(res["message"]));
				 $("#extract").val("재추출 시도");
			 } else {
				 $("#status").html(get_success_message("피드 추출 성공"));
				 $("#extract").val("추출 실행 완료");
				 $("#extract").button({disabled: true});
			 }
		 }
	 );
 };

 // setacl button event handler
 var setAclHandler = function() {
	 $("setacl").val("ACL 설정 중");
	 var feed_name = $("#feed_name").val();
	 var parent_name = $("#dir_list").val();
	 var sample_feed = $("#feed_list option:selected").val();
	 $.post(
		 ajax_url,
		 { "command": "setacl", "feed_name": feed_name, "parent_name": parent_name, "sample_feed": sample_feed },
		 function(data, textStatus, jqXHR) {
			 res = jQuery.parseJSON(data);
			 if (res["result"] != "0") {
				 $("#status").html(get_error_message(res["message"]));
			 } else {
				 $("#status").html(get_success_message("ACL 설정 성공"));
				 $("#setacl").val("ACL 설정 완료");
				 $("#setacl").button({disabled: true});
				 $("#feedly_link").attr('href, 'http://feedly.com/#subscription%2Ffeed%2Fhttp%3A%2F%2Fterzeron.net%2F' + feed_name + '.xml');
				 $("#feedly_link").css('display', 'block');
			 }
		 }
	 );
 };

 // reset button event handler
 var resetHandler = function() {
 	 $("#save").val("저장");
	 $("#save").button({disabled: false})
 	 $("#lint").val("XML lint 실행");
	 $("#lint").button({disabled: false})
 	 $("#extract").val("추출 실행");
	 $("#extract").button({disabled: false})
 	 $("#setacl").val("ACL 설정");
	 $("#setacl").button({disabled: false})
 	 $("#disable").val("비활성화");
	 $("#disable").button({disabled: false})
 	 $("#remove").val("삭제");
	 $("#remove").button({disabled: false})
 };
 
 // remove button event handler
 var removeHandler = function() {
	 $("remove").val("삭제 중");
	 //var feed_name = $("#feed_name").val();
	 var parent_name = $("#dir_list").val();
	 var sample_feed = $("#feed_list option:selected").val();
	 $.post(
		 ajax_url,
		 { "command": "remove", "parent_name": parent_name, "sample_feed": sample_feed },
		 function(data, textStatus, jqXHR) {
			 res = jQuery.parseJSON(data);
			 if (res["result"] != "0") {
				 $("#status").html(get_error_message(res["message"]));
			 } else {
				 $("#status").html(get_success_message("삭제 성공"));
				 $("#remove").val("삭제 완료");
				 $("#remove").button({disabled: true});
			 }
		 }
	 );
 };

 // remove button event handler
 var disableHandler = function() {
	 $("disable").val("비활성화 중");
	 //var feed_name = $("#feed_name").val();
	 var parent_name = $("#dir_list").val();
	 var sample_feed = $("#feed_list option:selected").val();
	 $.post(
		 ajax_url,
		 { "command": "disable", "parent_name": parent_name, "sample_feed": sample_feed },
		 function(data, textStatus, jqXHR) {
			 res = jQuery.parseJSON(data);
			 if (res["result"] != "0") {
				 $("#status").html(get_error_message(res["message"]));
			 } else {
				 $("#status").html(get_success_message("비활성화 성공"));
				 $("#disable").val("비활성화 완료");
				 $("#disable").button({disabled: true});
			 }
		 }
	 );
 };

 $("#save").button().click(saveHandler);
 $("#lint").button().click(lintHandler);
 $("#extract").button().click(extractHandler);
 $("#setacl").button().click(setAclHandler);
 $("#reset").button().click(resetHandler);
 $("#remove").button().click(removeHandler);
 $("#disable").button().click(disableHandler);

 function read_form_cdata() {
	 var cdata_arr = new Array();
	 var cdata = $(".cdata");
	 for (var i = 0; i < cdata.length; i++) {
		 cdata_arr[i] = cdata[i].value;
	 }
	 return cdata_arr;
 }

 var StringBuffer = function() {
	 this.buffer = new Array();
 }
 StringBuffer.prototype.append = function(obj) {
	 this.buffer.push(obj);
 }
 StringBuffer.prototype.toString = function() {
	 return this.buffer.join("");
 }

 function replace_form_with_cdata(cdata_arr) {
	 var xml_text = $("#xml").html();
	 // basic replacement
	 var regex = new RegExp("<br>", "g");
	 xml_text = xml_text.replace(regex, "");
	 regex = new RegExp("&nbsp;", "g");
	 xml_text = xml_text.replace(regex, " ");
	 regex = new RegExp("    ", "g");
	 xml_text = xml_text.replace(regex, "\t");
	 regex = new RegExp("&lt;", "g");
	 xml_text = xml_text.replace(regex, "<");
	 regex = new RegExp("&gt;", "g");
	 xml_text = xml_text.replace(regex, ">");

	 // split
	 var index = 0;
	 var i = 0;
	 var index_arr = new Array();
	 var start_pattern_str = "<![CDATA[";
	 var end_pattern_str = "]]>";
	 while (1) {
		 index = xml_text.indexOf(start_pattern_str, index);
		 if (index < 0 || index >= xml_text.length) {
			 break;
		 }
		 // 시작점
		 index_arr.push(index);
		 index = xml_text.indexOf(end_pattern_str, index);
		 if (index < 0 || index >= xml_text.length) {
			 break;
		 }
		 // 종료점
		 index_arr.push(index);
	 }
	 // concatenate
	 var new_xml_text = new StringBuffer();
	 var start = 0;
	 var j = 0;
	 for (var i = 0; i < index_arr.length; i+=2) {
		 // (시작점, 종료점) 두 개씩 꺼내서 그 가운데를 바꿔치기함
		 var i0 = index_arr[i];
		 var i1 = index_arr[i+1];
		 new_xml_text.append(xml_text.substr(start, i0 + start_pattern_str.length - start));
		 new_xml_text.append(cdata_arr[j++]);
		 new_xml_text.append(xml_text.substr(i1, end_pattern_str.length));
		 start = i1 + 3;
	 }
	 new_xml_text.append(xml_text.substr(start, xml_text.length - start));
	 return new_xml_text.toString();
 }
</script>
