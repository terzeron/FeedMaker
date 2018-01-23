#!/usr/bin/env python3

import sys
import os
import re
import time
import datetime
import getopt
import subprocess
from feedmakerutil import warn, die
import feedmakerutil
import PyRSS2Gen


SECONDS_PER_DAY = 60 * 60 * 24
MIN_CONTENT_LENGTH = 64
MAX_CONTENT_LENGTH = 64 * 1024
MAX_NUM_DAYS = 7


def get_pub_date_str(file_name):
    if os.path.isfile(file_name):
        ts = os.stat(file_name).st_mtime
    else:
        ts = datetime.datetime.now().timestamp()
    dt = datetime.datetime.fromtimestamp(float(ts))
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def get_rss_date_str(ts=datetime.datetime.now().timestamp()):
    dt = datetime.datetime.fromtimestamp(float(ts))
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def get_date_str(ts=datetime.datetime.now().timestamp()):
    dt = datetime.datetime.fromtimestamp(float(ts))
    return dt.strftime("%Y%m%d")


def get_list_file_name(list_dir, date_str):
    return "%s/%s.txt" % (list_dir, date_str)


def get_new_file_name(url):
    return "html/" + feedmakerutil.get_short_md5_name(url) + ".html"


def get_collection_configs(config):
    collection_conf = feedmakerutil.get_config_node(config, "collection")
    if collection_conf == None:
        die("can't get collection element")

    ignore_old_list = feedmakerutil.get_config_value(collection_conf, "ignore_old_list")
    ignore_old_list = bool("true" == ignore_old_list)
    is_completed = feedmakerutil.get_config_value(collection_conf, "is_completed")
    is_completed = bool("true" == is_completed)
    sort_field_pattern = feedmakerutil.get_config_value(collection_conf, "sort_field_pattern")
    unit_size_per_day = feedmakerutil.get_config_value(collection_conf, "unit_size_per_day")
    unit_size_per_day = float(unit_size_per_day) if unit_size_per_day else None

    post_process_script_list_conf = feedmakerutil.get_config_node(collection_conf, "post_process_script_list")
    if post_process_script_list_conf:
        post_process_script_list = feedmakerutil.get_all_config_values(post_process_script_list_conf, "post_process_script")
    else:
        post_process_script_list = []

    options = {
        "ignore_old_list": ignore_old_list,
        "is_completed": is_completed,
        "sort_field_pattern": sort_field_pattern,
        "unit_size_per_day": unit_size_per_day,
        "post_process_script_list": post_process_script_list
    }
    
    return options


def get_extraction_configs(config):
    extraction_conf = feedmakerutil.get_config_node(config, "extraction")
    if extraction_conf == None:
        die("can't get extraction element")

    render_js = feedmakerutil.get_config_value(extraction_conf, "render_js")
    render_js = bool("true" == render_js)
    force_sleep_between_articles = feedmakerutil.get_config_value(extraction_conf, "force_sleep_between_articles")
    force_sleep_between_articles = bool(force_sleep_between_articles and "true" == force_sleep_between_articles)
    bypass_element_extraction = feedmakerutil.get_config_value(extraction_conf, "bypass_element_extraction")
    bypass_element_extraction = bool("true" == bypass_element_extraction)
    review_point_threshold = feedmakerutil.get_config_value(extraction_conf, "review_point_threshold")
    user_agent = feedmakerutil.get_config_value(extraction_conf, "user_agent")
    referer = feedmakerutil.get_config_value(extraction_conf, "referer")

    post_process_script_list_conf = feedmakerutil.get_config_node(extraction_conf, "post_process_script_list")
    if post_process_script_list_conf:
        post_process_script_list = feedmakerutil.get_all_config_values(post_process_script_list_conf, "post_process_script")
    else:
        post_process_script_list = []

    options = {
        "render_js": render_js,
        "force_sleep_between_articles": force_sleep_between_articles,
        "bypass_element_extraction": bypass_element_extraction,
        "review_point_threshold": review_point_threshold,
        "user_agent": user_agent,
        "referer": referer,
        "post_process_script_list": post_process_script_list,
    }
    
    return options


def get_notification_configs(config):
    noti_conf = feedmakerutil.get_config_node(config, "notification")
    email = feedmakerutil.get_config_node(noti_conf, "email")
    recipient = feedmakerutil.get_config_value(email, "recipient")
    subject = feedmakerutil.get_config_value(email, "subject")
    return (email, recipient, subject)

    
def get_recent_list(list_dir, post_process_script_list):
    print("# get_recent_list(%s)" % (list_dir))

    date_str = get_date_str()
    new_list_file_name = get_list_file_name(list_dir, date_str)
    post_process_cmd = ""
    for script in post_process_script_list:
        if post_process_cmd:
            post_process_cmd += " |"
        post_process_cmd += ' %s "%s"' % (post_process_script, new_list_file_name)
    if post_process_cmd:
        post_process_cmd += " |"
    post_process_cmd += ' remove_duplicate_line.py > "%s"' % (new_list_file_name)

    cmd = "collect_new_list.py" + post_process_cmd
    print(cmd)
    result = feedmakerutil.exec_cmd(cmd)
    if result == False:
        die("can't collect new list from the page")

    with open(new_list_file_name, 'r', encoding='utf-8') as in_file:
        uniq_list = []
        for line in in_file:
            line = line.rstrip()
            if not line.startswith("# "):
                uniq_list.append(line)

    return uniq_list


def read_old_list_from_file(list_dir, is_completed):
    print("# read_old_list_from_file(list_dir=%s, is_completed=%r)" % (list_dir, is_completed))

    result_list = []
    ts = datetime.datetime.now().timestamp()
    if is_completed == False:
        # 아직 진행 중인 피드에 대해서는 현재 날짜에 가장 가까운
        # 과거 리스트 파일 1개를 찾아서 그 안에 기록된 리스트를 꺼냄

        list_file = ""
        i = 0
        # 과거까지 리스트가 존재하는지 확인
        for i in range(MAX_NUM_DAYS):
            date_str = get_date_str(ts - i * SECONDS_PER_DAY)
            list_file = get_list_file_name(list_dir, date_str)
            print(list_file)
            # 오늘에 가장 가까운 리스트가 존재하면 탈출
            if os.path.isfile(list_file):
                # read the old list
                with open(list_file, 'r', encoding='utf-8') as in_file:
                    for line in in_file:
                        line = line.rstrip()
                        if not line.startswith("# "):
                            result_list.append(line)
    else:
        # 이미 완료된 피드에 대해서는 기존 리스트를 모두 취합함
        for entry in os.scandir(list_dir):
            if entry.name.startswith(".") and entry.is_file():
                continue

            file_path = list_dir + "/" + entry.name
            with open(file_path, 'r', encoding='utf-8') as in_file:
                for line in in_file:
                    line = line.rstrip()
                    if not line.startswith("# "):
                        result_list.append(line)
    return list(set(result_list))


def get_rss_config_values(rss_config):
    rss_title = feedmakerutil.get_config_value(rss_config, "title")
    rss_description = feedmakerutil.get_config_value(rss_config, "description")
    rss_generator = feedmakerutil.get_config_value(rss_config, "generator")
    rss_copyright = feedmakerutil.get_config_value(rss_config, "copyright")
    rss_link = feedmakerutil.get_config_value(rss_config, "link")
    rss_language = feedmakerutil.get_config_value(rss_config, "language")
    rss_no_item_desc = feedmakerutil.get_config_value(rss_config, "no_item_desc")
    return (rss_title, rss_description, rss_generator, rss_copyright, rss_link, rss_language, rss_no_item_desc)
    

def generate_rss_feed(config, feed_list, rss_file_name):
    print("# generate_rss_feed(%s)" % (rss_file_name))

    rss_config = feedmakerutil.get_config_node(config, "rss")
    if rss_config == None:
        die("can't get rss element")
    
    (rss_title, rss_description, rss_generator, rss_copyright, rss_link, rss_language, rss_no_item_desc) = get_rss_config_values(rss_config)

    last_build_date_str = get_rss_date_str()
    date_str = get_date_str()
    temp_rss_file_name = rss_file_name + "." + date_str

    rss_items = []
    for feed_item in feed_list:
        (article_url, article_title) = feed_item.split('\t')
        new_file_name = get_new_file_name(article_url)
        guid = feedmakerutil.get_short_md5_name(article_url)
        pub_date_str = get_rss_date_str()
        
        content = ""
        with open(new_file_name, 'r', encoding='utf-8') as in_file:
            print("adding '%s' to the result" % (new_file_name))
            for line in in_file:
                content += line
                # restrict big contents
                if len(content) >= MAX_CONTENT_LENGTH:
                    content = "<strong>본문이 너무 길어서 전문을 싣지 않았습니다. 다음의 원문 URL을 참고해주세요.</strong><br/>" + content
                    break
            rss_items.append(
                PyRSS2Gen.RSSItem(
                    title=article_title,
                    link=article_url,
                    guid=article_url,
                    pubDate=pub_date_str,
                    description=content
                )
            )

    rss = PyRSS2Gen.RSS2(
        title=rss_title,
        link=rss_link,
        description=rss_description,
        lastBuildDate=last_build_date_str,
        items=rss_items
    )
    rss.write_xml(open(temp_rss_file_name, 'w'), encoding='utf-8')

    # 이번에 만들어진 rss 파일이 이전 파일과 내용이 다른지 확인
    is_different = False
    if os.path.isfile(rss_file_name):
        cmd = 'diff "%s" "%s" | grep -v -Ee \"(^(<|>) <(pub_date|last_build_date))|(^---\$)|(^[0-9,]+[a-z][0-9,]+\$)\" | wc -c' % (temp_rss_file_name, rss_file_name)
        print(cmd)
        result = feedmakerutil.exec_cmd(cmd)
        print(result)
        m = re.search(r'^\s*(?P<num_of_different_lines>\d+)\s*$', result)
        if m and m.group("num_of_different_lines") != "0":
            is_different = True
    else:
        is_different = True

    if is_different == True:
        # 이전 파일을 old 파일로 이름 바꾸기
        if os.path.isfile(rss_file_name):
            cmd = 'mv -f "%s" "%s.old"' % (rss_file_name, rss_file_name)
            print(cmd)
            result = feedmakerutil.exec_cmd(cmd)
            if result == False:
                return False
        # 이번에 만들어진 파일을 정식 파일 이름으로 바꾸기
        if os.path.isfile(temp_rss_file_name):
            cmd = 'mv -f "%s" "%s"' % (temp_rss_file_name, rss_file_name)
            print(cmd)
            result = feedmakerutil.exec_cmd(cmd)
    else:
        # 이번에 만들어진 파일을 지우기
        cmd = 'rm -f "%s"' % (temp_rss_file_name)
        print(cmd)
        result = feedmakerutil.exec_cmd(cmd)

    if result == False:
        return False
    return True


def determine_crawler_options(options):
    option_str = ""
    if "true" == options["render_js"]:
        option_str += " --render-js"
    if options["user_agent"]:
        option_str += " --ua '%s'" % (options["user_agent"])
    if options["referer"]:
        option_str += " --referer '%s'" % (options["referer"])

    '''
    #print("title=%s, review_point=%d, review_point_threshold=%f" % (title, review_point, review_point_threshold))
    if review_point and review_point_threshold and review_point > review_point_threshold:
        # 일반적으로 평점이 사용되지 않는 경우나
        # 평점이 기준치를 초과하는 경우에만 추출
        warn("ignore an article due to the low score")
        return 0
    '''
    
    return option_str


def append_item_to_result(feed_list, item, rss_file_name, options):
    fields = item.split('\t')
    review_point = None
    if len(fields) == 2:
        (url, title) = fields
    elif len(fields) == 3:
        (url, title, review_point) = fields
    new_file_name = get_new_file_name(url)
    size = 0
    
    if os.path.isfile(new_file_name) and os.stat(new_file_name).st_size >= MIN_CONTENT_LENGTH:
        # 이미 성공적으로 만들어져 있으니까 피드 리스트에 추가
        print("Success: %s: %s --> %s: %d" % (title, url, new_file_name, os.stat(new_file_name).st_size))
        feed_list.append(item)
    else:
        # 파일이 존재하지 않거나 크기가 작으니 다시 생성 시도
        cmd = determine_cmd(options, url, new_file_name)
        print(cmd)
        result = feedmakerutil.exec_cmd(cmd)
        if result == False:
            die("can't extract HTML elements")
        
        md5_name = feedmakerutil.get_short_md5_name(url)
        size = os.stat(new_file_name).st_size
        if size > 0:
            cmd = 'echo "<img src=\'http://terzeron.net/img/1x1.jpg?feed=%s&item=%s\'/>" >> "%s"' % (rss_file_name, md5_name, new_file_name)
            print(cmd)
            result = feedmakerutil.exec_cmd(cmd)
            if result == False:
                die("can't append page view logging tag")
        
        size = os.stat(new_file_name).st_size
        if size < MIN_CONTENT_LENGTH:
            # 피드 리스트에서 제외
            warn("%s: %s --> %s: %d (< %d byte)" % (title, url, new_file_name, size, MIN_CONTENT_LENGTH))
            return 0
        else:
            # 피드 리스트에 추가
            print("Success: %s: %s --> %s: %d" % (title, url, new_file_name, size))
            feed_list.append(item)

        if options["force_sleep_between_articles"]:
            time.sleep(1)


def determine_cmd(options, url, new_file_name):
    post_process_cmd = ""
    for script in options["post_process_script_list"]:
        post_process_cmd += ' | %s "%s"' % (script, url)

    if options["bypass_element_extraction"]:
        extraction_cmd = ""
    else:
        extraction_cmd = ' | extract.py "%s"' % url

    option_str = determine_crawler_options(options)
    cmd = 'crawler.sh %s "%s" %s %s > "%s"' % (option_str, url, extraction_cmd, post_process_cmd, new_file_name) 

    return cmd
            

def diff_old_and_recent(config, recent_list, old_list, feed_list, rss_file_name):
    print("# diff_old_and_recent(len(recent_list)=%d, len(old_list)=%d), len(feed_list)=%d, rss_file_name=%s" % (len(recent_list), len(old_list), len(feed_list), rss_file_name))

    options = get_extraction_configs(config)
    print("extraction options=", options)
        
    old_map = {}
    for old in old_list:
        if re.search(r'^\#', old):
            continue
        (url, title) = old.split('\t')
        old_map[url] = title
    #print(len(old_list))

    # differentiate
    result_list = []
    for recent in recent_list:
        if re.search(r'^\#', recent):
            continue
        
        (url, title) = recent.split('\t')
        if url not in old_map:
            result_list.append(recent)
            print("not exists %s" % (recent))
        else:
            print("exists %s" % (recent))

    # collect items to be generated as RSS feed
    print("Appending %d new items to the feed list" % (len(result_list)))
    for new_item in reversed(result_list):
        if re.search(r'^\#', new_item):
            continue
        append_item_to_result(feed_list, new_item, rss_file_name, options)
    
    print("Appending %d old items to the feed list" % (len(old_list)))
    for old_item in reversed(old_list):
        if re.search(r'^\#', old_item):
            continue
        append_item_to_result(feed_list, old_item, rss_file_name, options)

    if len(feed_list) == 0:
        print("_notice: 새로 추가된 feed가 없으므로 결과 파일을 변경하지 않음")
        return False
    return True

    
def get_start_idx(file_name):
    print("# get_start_idx(%s)" % (file_name))

    if os.path.isfile(file_name):
        with open(file_name, 'r', encoding='utf-8') as in_file:
            line = in_file.readline()
            start_idx = 0
            mtime = 0
            m = re.search(r'(?P<start_idx>\d+)\t(?P<mtime>\d+)', line)
            if m:
                start_idx = int(m.group("start_idx"))
                mtime = int(m.group("mtime"))
                
                print("start index: %d" % (start_idx))
                print("last modified time: %d, %s" % (mtime, get_rss_date_str(mtime)))
                return (start_idx, mtime)

    # 처음 생성 시
    write_next_start_idx(file_name, 0)
    ts = datetime.datetime.now().timestamp()
    return (0, int(ts))


def write_next_start_idx(file_name, next_start_idx):
    print("# write_next_start_idx(%s, %d)" % (file_name, next_start_idx))

    ts = datetime.datetime.now().timestamp()
    with open(file_name, 'w', encoding='utf-8') as out_file:
        print("next start index: %d" % (next_start_idx))
        print("current time: %d, %s" % (ts, get_rss_date_str(ts)))
        out_file.write("%d\t%d\n" % (int(next_start_idx), int(ts)))


def print_usage():
    print("usage:\t%s\t<config file> <rss file>" % (sys.argv[0]))
    print()


def cmp_int_or_str(a, b):
    m1 = re.search(r'^\d+$', a["sf"])
    m2 = re.search(r'^\d+$', b["sf"])
    if m1 and m2:
        return (int(a["sf"]) - int(b["sf"]))
    else:
        if a["sf"] < b["sf"]:
            return -1
        elif a["sf"] > b["sf"]:
            return 1
        else:
            return 0


def cmp_to_key(mycmp):
    class K:
        def __init__(self, obj, *args):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K

    
def main():
    print("=========================================================")
    print(" " + os.getcwd() + " ")
    print("=========================================================")

    do_collect_by_force = False
               
    optlist, args = getopt.getopt(sys.argv[1:], "c")
    for o, a in optlist:
        if o == '-c':
            do_collect_by_force = True
               
    if len(args) == 0:
        print_usage()
        sys.exit(-1)
               
    rss_file_name = args[0]

    config = feedmakerutil.read_config()
    if config == None:
        die("can't find conf.xml file nor get config element")
    options = get_collection_configs(config)
    print("collection options=", options)

    # -c 옵션이 지정된 경우, 설정의 is_completed 값 무시
    if do_collect_by_force:
        is_completed = False

    list_dir = "newlist"
    feedmakerutil.make_path(list_dir)
    feedmakerutil.make_path("html")

    # 과거 피드항목 리스트를 가져옴
    feed_list = []
    old_list = read_old_list_from_file(list_dir, options["is_completed"])
    if not old_list:
        warn("can't get old list!")

    # 완결여부 설정값 판단 
    recent_list = []
    if options["is_completed"]:
        # 완결된 피드는 적재된 리스트에서 일부 피드항목을 꺼내옴

        # 오름차순 정렬
        feed_id_sort_field_list = []
        feed_item_existence_set = set([])

        for i, old_item in enumerate(old_list):
            sort_field = ""
            m = re.search(options["sort_field_pattern"], old_item)
            if m:
                sort_field = m.group(1)
            else:
                warn("can't match the pattern /%s/" % (options["sort_field_pattern"]))
            
            if old_item not in feed_item_existence_set:
                feed_id_sort_field = {}
                feed_id_sort_field["id"] = i
                feed_id_sort_field["sf"] = sort_field
                feed_item_existence_set.add(old_item)
                feed_id_sort_field_list.append(feed_id_sort_field)

        sorted_feed_list = sorted(feed_id_sort_field_list, key=cmp_to_key(cmp_int_or_str))
        idx_file = "start_idx.txt"
        window_size = 10 # feedly initial max window size
        (start_idx, mtime) = get_start_idx(idx_file)
        end_idx = start_idx + window_size
        for i, feed in enumerate(sorted_feed_list):
            if i >= start_idx and i < end_idx:
                feed_list.append(old_list[feed["id"]])
                (url, title) = old_list[feed["id"]].split("\t")
                guid = feedmakerutil.get_short_md5_name(url)
                print("%s\t%s\t%s" % (url, title, guid))

        ts = datetime.datetime.now().timestamp()
        increment_size = int(((int(ts) - mtime) * options["unit_size_per_day"]) / 86400)
        print("# start_idx=%d, end_idx=%d, current time=%d, mtime=%d, window_size=%d, increment_size=%d" % (start_idx, end_idx, int(ts), mtime, window_size, increment_size))
        if increment_size > 0:
            write_next_start_idx(idx_file, start_idx + increment_size)
    else:
        # 피딩 중인 피드는 최신 피드항목을 받아옴
        recent_list = get_recent_list(list_dir, options["post_process_script_list"])
        if not recent_list:
            die("can't get recent list!")
        
        # 과거 피드항목 리스트와 최근 피드항목 리스트를 비교함
        if options["ignore_old_list"]:
            old_list = []
            feed_list = recent_list
        
        if not diff_old_and_recent(config, recent_list, old_list, feed_list, rss_file_name):
            return -1

    if not do_collect_by_force:
        # generate RSS feed
        if not generate_rss_feed(config, feed_list, rss_file_name):
            return -1
    
    # upload RSS feed file
    cmd = 'upload.py %s' % (rss_file_name)
    print(cmd)
    result = feedmakerutil.exec_cmd(cmd)
    print(result)
    if result == False:
        return -1

    m = re.search(r'Upload: success', result)
    if m and do_collect_by_force == False:
        # email notification
        (email, recipient, subject) = get_notification_configs(config)
        if email and recipient and subject:
            cmd = "| mail -s '%s' '%s'" % (subject, recipient)
            with subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE) as p:
                for feed in recent_list:
                    p.write(feed + "\n")
            print("sent a notification in mail")
    return 0


if __name__ == "__main__":
    sys.exit(main())
